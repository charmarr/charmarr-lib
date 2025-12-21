# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""StatefulSet patching utilities for shared storage volumes.

This module provides functions to mount a shared PVC into a StatefulSet
managed by Juju. Used by charms that need to access the shared media
storage PVC created by the charmarr-storage charm.

Key concepts:
- Volume: A pod-level definition that references a PVC
- VolumeMount: A container-level mount point for a volume

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
        )

See ADR: storage/adr-003-pvc-patching-in-arr-charms.md
"""

from lightkube.models.core_v1 import (
    Container,
    PersistentVolumeClaimVolumeSource,
    Volume,
    VolumeMount,
)
from lightkube.resources.apps_v1 import StatefulSet

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
) -> dict:
    """Build a strategic merge patch for adding storage volume.

    The patch adds:
    1. A volume referencing the PVC
    2. A volumeMount in the specified container

    Strategic merge patch merges arrays by the 'name' field,
    so existing volumes and containers are preserved.
    """
    volume = Volume(
        name=volume_name,
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName=pvc_name),
    )
    mount = VolumeMount(name=volume_name, mountPath=mount_path)
    container = Container(name=container_name, volumeMounts=[mount])

    return {
        "spec": {
            "template": {
                "spec": {
                    "volumes": [volume.to_dict()],
                    "containers": [container.to_dict()],
                }
            }
        }
    }


def _build_remove_storage_patch(
    sts: StatefulSet,
    container_name: str,
    volume_name: str,
) -> dict:
    """Build a patch to remove a storage volume and its mount.

    Kubernetes doesn't support removing array items by name in patches -
    we must replace the entire array with the item filtered out.
    """
    if sts.spec is None or sts.spec.template.spec is None:
        return {}

    pod_spec = sts.spec.template.spec
    filtered_volumes = [v.to_dict() for v in (pod_spec.volumes or []) if v.name != volume_name]

    containers_patch = []
    for container in pod_spec.containers or []:
        if container.name == container_name:
            filtered_mounts = [
                m.to_dict() for m in (container.volumeMounts or []) if m.name != volume_name
            ]
            containers_patch.append({"name": container_name, "volumeMounts": filtered_mounts})
        else:
            containers_patch.append({"name": container.name})

    return {
        "spec": {
            "template": {
                "spec": {
                    "volumes": filtered_volumes,
                    "containers": containers_patch,
                }
            }
        }
    }


def reconcile_storage_volume(
    manager: K8sResourceManager,
    statefulset_name: str,
    namespace: str,
    container_name: str,
    pvc_name: str | None,
    mount_path: str = _DEFAULT_MOUNT_PATH,
    volume_name: str = _DEFAULT_VOLUME_NAME,
) -> ReconcileResult:
    """Reconcile shared storage PVC volume and mount on a StatefulSet.

    This function ensures a shared PVC is mounted (or unmounted) in a
    Juju-managed StatefulSet. It's idempotent.

    If pvc_name is None, the volume is removed. If pvc_name is provided,
    the volume is mounted.

    Args:
        manager: K8sResourceManager instance.
        statefulset_name: Name of the StatefulSet (usually self.app.name).
        namespace: Kubernetes namespace (usually self.model.name).
        container_name: Container name from charmcraft.yaml (NOT self.app.name!).
        pvc_name: Name of the PVC to mount, or None to unmount.
        mount_path: Path where the volume should be mounted.
        volume_name: Name for the volume definition.

    Returns:
        ReconcileResult indicating if changes were made.

    Raises:
        ApiError: If the StatefulSet doesn't exist or patch fails.

    Example:
        # Mount storage when relation data is available
        result = reconcile_storage_volume(
            manager,
            statefulset_name=self.app.name,
            namespace=self.model.name,
            container_name="radarr",
            pvc_name=storage_data.pvc_name if storage_data else None,
        )
    """
    sts = manager.get(StatefulSet, statefulset_name, namespace)
    currently_mounted = is_storage_mounted(sts, container_name, volume_name)

    if pvc_name is None:
        if not currently_mounted:
            return ReconcileResult(changed=False, message="Storage not mounted")
        patch = _build_remove_storage_patch(sts, container_name, volume_name)
        manager.patch(StatefulSet, statefulset_name, patch, namespace)
        return ReconcileResult(changed=True, message=f"Removed volume {volume_name}")

    if currently_mounted:
        return ReconcileResult(changed=False, message="Storage already mounted")

    patch = _build_storage_patch(container_name, pvc_name, mount_path, volume_name)
    manager.patch(StatefulSet, statefulset_name, patch, namespace)
    return ReconcileResult(changed=True, message=f"Mounted {pvc_name} at {mount_path}")
