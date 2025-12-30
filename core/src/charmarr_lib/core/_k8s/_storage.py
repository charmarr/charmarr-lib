# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""StatefulSet patching utilities for shared storage volumes.

This module provides functions to mount a shared PVC into a StatefulSet
managed by Juju. Used by charms that need to access the shared media
storage PVC created by the charmarr-storage charm.

Key concepts:
- Volume: A pod-level definition that references a PVC
- VolumeMount: A container-level mount point for a volume
- SecurityContext: Pod-level fsGroup for volume permissions

Critical gotcha:
    The container_name parameter MUST match the container name in
    charmcraft.yaml, NOT the Juju application name (self.app.name).

    Example:
        # In charmcraft.yaml:
        containers:
          radarr:  # <- This is the container name
            resource: oci-image

        # In charm code:
        reconcile_storage_volume(
            manager,
            statefulset_name=self.app.name,  # Could be "radarr-4k"
            namespace=self.model.name,
            container_name="radarr",  # MUST match charmcraft.yaml, not app.name!
            pvc_name=storage_data.pvc_name,
            mount_path=storage_data.mount_path,
            pgid=storage_data.pgid,
        )

See ADR: storage/adr-003-pvc-patching-in-arr-charms.md
"""

from lightkube.models.core_v1 import (
    Container,
    PersistentVolumeClaimVolumeSource,
    PodSecurityContext,
    Volume,
    VolumeMount,
)
from lightkube.resources.apps_v1 import StatefulSet
from lightkube.types import PatchType

from charmarr_lib.krm import K8sResourceManager, ReconcileResult

_DEFAULT_VOLUME_NAME = "charmarr-shared-data"
_DEFAULT_MOUNT_PATH = "/data"


def _has_volume(sts: StatefulSet, volume_name: str) -> bool:
    """Check if a StatefulSet has a volume with the given name."""
    if sts.spec is None or sts.spec.template.spec is None:
        return False
    volumes = sts.spec.template.spec.volumes or []
    return any(v.name == volume_name for v in volumes)


def _has_volume_mount(sts: StatefulSet, container_name: str, mount_name: str) -> bool:
    """Check if a container has a volume mount with the given name."""
    if sts.spec is None or sts.spec.template.spec is None:
        return False
    containers = sts.spec.template.spec.containers or []
    for container in containers:
        if container.name == container_name:
            mounts = container.volumeMounts or []
            return any(m.name == mount_name for m in mounts)
    return False


def is_storage_mounted(
    sts: StatefulSet,
    container_name: str,
    volume_name: str = _DEFAULT_VOLUME_NAME,
) -> bool:
    """Check if shared storage is already mounted in a StatefulSet.

    Args:
        sts: The StatefulSet to check.
        container_name: Name of the container (from charmcraft.yaml).
        volume_name: Name of the volume.

    Returns:
        True if both the volume and its mount exist, False otherwise.
    """
    return _has_volume(sts, volume_name) and _has_volume_mount(sts, container_name, volume_name)


def _build_storage_patch(
    container_name: str,
    pvc_name: str,
    mount_path: str,
    volume_name: str,
    pgid: int | None = None,
) -> dict:
    """Build a strategic merge patch for adding storage volume.

    The patch adds:
    1. A volume referencing the PVC
    2. A volumeMount in the specified container
    3. Optionally, a securityContext with fsGroup for volume permissions

    Strategic merge patch merges arrays by the 'name' field,
    so existing volumes and containers are preserved.
    """
    volume = Volume(
        name=volume_name,
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName=pvc_name),
    )
    mount = VolumeMount(name=volume_name, mountPath=mount_path)
    container = Container(name=container_name, volumeMounts=[mount])

    pod_spec: dict = {
        "volumes": [volume.to_dict()],
        "containers": [container.to_dict()],
    }

    if pgid is not None:
        security_context = PodSecurityContext(fsGroup=pgid)
        pod_spec["securityContext"] = security_context.to_dict()

    return {
        "spec": {
            "template": {
                "spec": pod_spec,
            }
        }
    }


def _find_volume_index(volumes: list[Volume], name: str) -> int | None:
    """Find the index of a volume by name."""
    for i, vol in enumerate(volumes):
        if vol.name == name:
            return i
    return None


def _find_mount_index(mounts: list[VolumeMount], name: str) -> int | None:
    """Find the index of a volume mount by name."""
    for i, mount in enumerate(mounts):
        if mount.name == name:
            return i
    return None


def _build_remove_storage_json_patch(
    sts: StatefulSet,
    container_name: str,
    volume_name: str,
) -> list[dict]:
    """Build JSON patch operations to remove a storage volume, mount, and securityContext.

    Returns a list of JSON patch operations that remove:
    1. The volume from spec.template.spec.volumes
    2. The volumeMount from the target container
    3. The securityContext from the pod spec (if present)
    """
    if sts.spec is None or sts.spec.template.spec is None:
        return []

    pod_spec = sts.spec.template.spec
    operations: list[dict] = []

    volumes = pod_spec.volumes or []
    volume_idx = _find_volume_index(volumes, volume_name)
    if volume_idx is not None:
        operations.append({"op": "remove", "path": f"/spec/template/spec/volumes/{volume_idx}"})

    containers = pod_spec.containers or []
    for ci, container in enumerate(containers):
        if container.name == container_name:
            mounts = container.volumeMounts or []
            mount_idx = _find_mount_index(mounts, volume_name)
            if mount_idx is not None:
                operations.append(
                    {
                        "op": "remove",
                        "path": f"/spec/template/spec/containers/{ci}/volumeMounts/{mount_idx}",
                    }
                )
            break

    if pod_spec.securityContext is not None:
        operations.append({"op": "remove", "path": "/spec/template/spec/securityContext"})

    return operations


def reconcile_storage_volume(
    manager: K8sResourceManager,
    statefulset_name: str,
    namespace: str,
    container_name: str,
    pvc_name: str | None,
    mount_path: str = _DEFAULT_MOUNT_PATH,
    volume_name: str = _DEFAULT_VOLUME_NAME,
    pgid: int | None = None,
) -> ReconcileResult:
    """Reconcile shared storage PVC volume and mount on a StatefulSet.

    This function ensures a shared PVC is mounted (or unmounted) in a
    Juju-managed StatefulSet. Uses strategic merge patch which is idempotent.

    If pvc_name is None, the volume is removed. If pvc_name is provided,
    the volume is mounted.

    When pgid is provided, the pod's SecurityContext is set with fsGroup.
    This ensures files on the shared storage have the correct group ownership.

    Args:
        manager: K8sResourceManager instance.
        statefulset_name: Name of the StatefulSet (usually self.app.name).
        namespace: Kubernetes namespace (usually self.model.name).
        container_name: Container name from charmcraft.yaml (NOT self.app.name!).
        pvc_name: Name of the PVC to mount, or None to unmount.
        mount_path: Path where the volume should be mounted.
        volume_name: Name for the volume definition.
        pgid: Group ID for fsGroup (from storage relation).

    Returns:
        ReconcileResult indicating if changes were made.

    Raises:
        ApiError: If the StatefulSet doesn't exist or patch fails.

    Example:
        result = reconcile_storage_volume(
            manager,
            statefulset_name=self.app.name,
            namespace=self.model.name,
            container_name="radarr",
            pvc_name=storage_data.pvc_name if storage_data else None,
            mount_path=storage_data.mount_path,
            pgid=storage_data.pgid,
        )
    """
    if pvc_name is None:
        sts = manager.get(StatefulSet, statefulset_name, namespace)
        if not is_storage_mounted(sts, container_name, volume_name):
            return ReconcileResult(changed=False, message="Storage not mounted")
        patch_ops = _build_remove_storage_json_patch(sts, container_name, volume_name)
        if patch_ops:
            manager.patch(StatefulSet, statefulset_name, patch_ops, namespace, PatchType.JSON)
        return ReconcileResult(changed=True, message=f"Removed volume {volume_name}")

    patch = _build_storage_patch(container_name, pvc_name, mount_path, volume_name, pgid)
    manager.patch(StatefulSet, statefulset_name, patch, namespace)
    return ReconcileResult(changed=True, message=f"Storage configured at {mount_path}")
