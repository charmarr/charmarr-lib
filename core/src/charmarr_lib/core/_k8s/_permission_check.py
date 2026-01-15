# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Permission checking utilities for shared storage volumes.

This module provides functions to verify that a given puid/pgid can write
to a mounted PVC. Uses a short-lived Kubernetes Job to test permissions.

Use case:
    The charmarr-storage charm needs to detect permission mismatches early,
    rather than having consumer charms fail silently. This module creates
    a Job that attempts to write a test file as the configured user/group.
"""

import logging
from dataclasses import dataclass
from enum import Enum

from lightkube import ApiError
from lightkube.models.batch_v1 import JobSpec
from lightkube.models.core_v1 import (
    Container,
    PersistentVolumeClaimVolumeSource,
    PodSpec,
    PodTemplateSpec,
    SecurityContext,
    Volume,
    VolumeMount,
)
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.batch_v1 import Job
from tenacity import retry, retry_if_result, stop_after_delay, wait_fixed

from charmarr_lib.krm import K8sResourceManager

logger = logging.getLogger(__name__)

_JOB_NAME_PREFIX = "charmarr-permission-check"
_TEST_FILE = ".charmarr-permission-test"
_LABEL_PUID = "charmarr.io/puid"
_LABEL_PGID = "charmarr.io/pgid"


class PermissionCheckStatus(str, Enum):
    """Status of a permission check."""

    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
    NOT_RUN = "not_run"


@dataclass
class PermissionCheckResult:
    """Result of a storage permission check."""

    status: PermissionCheckStatus
    message: str


def _get_job_name(pvc_name: str) -> str:
    """Generate Job name from PVC name."""
    return f"{_JOB_NAME_PREFIX}-{pvc_name[:20]}"


def _build_permission_check_job(
    job_name: str,
    namespace: str,
    pvc_name: str,
    puid: int,
    pgid: int,
    mount_path: str,
) -> Job:
    """Build a Job that tests write permissions on the PVC."""
    test_path = f"{mount_path}/{_TEST_FILE}"
    command = [
        "sh",
        "-c",
        f"touch {test_path} && rm {test_path} && echo 'Permission check passed'",
    ]

    container = Container(
        name="permission-check",
        image="busybox:latest",
        command=command,
        securityContext=SecurityContext(
            runAsUser=puid,
            runAsGroup=pgid,
        ),
        volumeMounts=[
            VolumeMount(name="test-volume", mountPath=mount_path),
        ],
    )

    volume = Volume(
        name="test-volume",
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName=pvc_name),
    )

    return Job(
        metadata=ObjectMeta(
            name=job_name,
            namespace=namespace,
            labels={
                "app.kubernetes.io/managed-by": "charmarr-storage",
                _LABEL_PUID: str(puid),
                _LABEL_PGID: str(pgid),
            },
        ),
        spec=JobSpec(
            ttlSecondsAfterFinished=300,
            backoffLimit=0,
            template=PodTemplateSpec(
                spec=PodSpec(
                    restartPolicy="Never",
                    containers=[container],
                    volumes=[volume],
                ),
            ),
        ),
    )


def _get_job_status(job: Job) -> PermissionCheckStatus:
    """Determine permission check status from Job state."""
    if job.status is None:
        return PermissionCheckStatus.PENDING

    if job.status.succeeded and job.status.succeeded > 0:
        return PermissionCheckStatus.PASSED

    if job.status.failed and job.status.failed > 0:
        return PermissionCheckStatus.FAILED

    return PermissionCheckStatus.PENDING


def _job_config_matches(job: Job, puid: int, pgid: int) -> bool:
    """Check if existing Job was created with the same puid/pgid."""
    if job.metadata is None or job.metadata.labels is None:
        return False

    labels = job.metadata.labels
    job_puid = labels.get(_LABEL_PUID)
    job_pgid = labels.get(_LABEL_PGID)

    return job_puid == str(puid) and job_pgid == str(pgid)


def _is_pending(result: PermissionCheckResult) -> bool:
    """Check if result is still pending (used for retry condition)."""
    return result.status == PermissionCheckStatus.PENDING


def _make_poll_job_status(
    manager: "K8sResourceManager",
    job_name: str,
    namespace: str,
    puid: int,
    pgid: int,
):
    """Create a polling function for Job status with tenacity retry."""

    @retry(
        stop=stop_after_delay(30),
        wait=wait_fixed(2),
        retry=retry_if_result(_is_pending),
    )
    def poll() -> PermissionCheckResult:
        job = manager.get(Job, job_name, namespace)
        status = _get_job_status(job)

        if status == PermissionCheckStatus.PASSED:
            return PermissionCheckResult(
                status=PermissionCheckStatus.PASSED,
                message="Storage permissions OK",
            )
        if status == PermissionCheckStatus.FAILED:
            return PermissionCheckResult(
                status=PermissionCheckStatus.FAILED,
                message=f"Storage permission denied for puid={puid} pgid={pgid}. "
                "Check ownership on storage backend.",
            )
        return PermissionCheckResult(
            status=PermissionCheckStatus.PENDING,
            message="Permission check in progress",
        )

    return poll


def check_storage_permissions(
    manager: K8sResourceManager,
    namespace: str,
    pvc_name: str,
    puid: int,
    pgid: int,
    mount_path: str = "/data",
) -> PermissionCheckResult:
    """Check if puid/pgid can write to the mounted PVC.

    Creates a short-lived Kubernetes Job that attempts to create and delete
    a test file on the mounted storage as the specified user/group.

    The Job is created if it doesn't exist, and its status is checked on
    subsequent calls. Jobs are automatically cleaned up after 5 minutes
    via ttlSecondsAfterFinished.

    Args:
        manager: K8sResourceManager instance.
        namespace: Kubernetes namespace.
        pvc_name: Name of the PVC to test.
        puid: User ID to test write permissions as.
        pgid: Group ID to test write permissions as.
        mount_path: Path where the PVC is mounted.

    Returns:
        PermissionCheckResult with status and message.

    Example:
        result = check_storage_permissions(
            manager=self.k8s,
            namespace=self.model.name,
            pvc_name="charmarr-shared-media",
            puid=1000,
            pgid=1000,
        )
        if result.status == PermissionCheckStatus.FAILED:
            # Block charm with permission error message
    """
    job_name = _get_job_name(pvc_name)

    try:
        job = manager.get(Job, job_name, namespace)
    except ApiError as e:
        if e.status.code != 404:
            raise
        job = None

    # If Job exists but config changed, delete it so we can create a new one
    if job is not None and not _job_config_matches(job, puid, pgid):
        logger.info(
            "Permission check Job %s config changed, recreating with puid=%d pgid=%d",
            job_name,
            puid,
            pgid,
        )
        manager.delete(Job, job_name, namespace)
        job = None

    if job is None:
        job = _build_permission_check_job(
            job_name=job_name,
            namespace=namespace,
            pvc_name=pvc_name,
            puid=puid,
            pgid=pgid,
            mount_path=mount_path,
        )
        logger.info("Creating permission check Job %s for PVC %s", job_name, pvc_name)
        manager.apply(job)

    status = _get_job_status(job)

    if status == PermissionCheckStatus.PASSED:
        return PermissionCheckResult(
            status=PermissionCheckStatus.PASSED,
            message="Storage permissions OK",
        )

    if status == PermissionCheckStatus.FAILED:
        return PermissionCheckResult(
            status=PermissionCheckStatus.FAILED,
            message=f"Storage permission denied for puid={puid} pgid={pgid}. "
            "Check ownership on storage backend.",
        )

    # Job is PENDING - poll until it completes or times out
    logger.info("Waiting for permission check Job %s to complete", job_name)
    poll = _make_poll_job_status(manager, job_name, namespace, puid, pgid)
    return poll()


def delete_permission_check_job(
    manager: K8sResourceManager,
    namespace: str,
    pvc_name: str,
) -> bool:
    """Delete the permission check Job if it exists.

    Useful for forcing a re-check when puid/pgid config changes.

    Args:
        manager: K8sResourceManager instance.
        namespace: Kubernetes namespace.
        pvc_name: Name of the PVC the Job was created for.

    Returns:
        True if Job was deleted, False if it didn't exist.
    """
    job_name = _get_job_name(pvc_name)

    try:
        manager.delete(Job, job_name, namespace)
        logger.info("Deleted permission check Job %s", job_name)
        return True
    except ApiError as e:
        if e.status.code == 404:
            return False
        raise
