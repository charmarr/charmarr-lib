# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""StatefulSet patching utilities for hardware device access.

This module provides functions to mount host devices (like /dev/dri for
Intel QuickSync) into a StatefulSet managed by Juju. Used by charms that
need hardware transcoding capabilities (Plex, Jellyfin).

Key concepts:
- HostPath volume: Mounts a path from the host node into the pod
- Device access: /dev/dri provides GPU access for hardware transcoding

See ADR: apps/adr-009-plex.md (hardware transcoding section)
"""

from lightkube.models.core_v1 import (
    Container,
    HostPathVolumeSource,
    Volume,
    VolumeMount,
)
from lightkube.resources.apps_v1 import StatefulSet

from charmarr_lib.krm import K8sResourceManager, ReconcileResult

_DRI_VOLUME_NAME = "dev-dri"
_DRI_HOST_PATH = "/dev/dri"
_DRI_MOUNT_PATH = "/dev/dri"


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


def is_hardware_device_mounted(
    sts: StatefulSet,
    container_name: str,
    volume_name: str = _DRI_VOLUME_NAME,
) -> bool:
    """Check if hardware device is already mounted in a StatefulSet.

    Args:
        sts: The StatefulSet to check.
        container_name: Name of the container (from charmcraft.yaml).
        volume_name: Name of the volume.

    Returns:
        True if both the volume and its mount exist, False otherwise.
    """
    return _has_volume(sts, volume_name) and _has_volume_mount(sts, container_name, volume_name)


def _build_hardware_device_patch(
    container_name: str,
    host_path: str,
    mount_path: str,
    volume_name: str,
) -> dict:
    """Build a strategic merge patch for adding hardware device volume."""
    volume = Volume(
        name=volume_name,
        hostPath=HostPathVolumeSource(path=host_path, type="Directory"),
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


def _build_remove_hardware_device_json_patch(
    sts: StatefulSet,
    container_name: str,
    volume_name: str,
) -> list[dict]:
    """Build JSON patch operations to remove a hardware device volume and mount."""
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

    return operations


def reconcile_hardware_transcoding(
    manager: K8sResourceManager,
    statefulset_name: str,
    namespace: str,
    container_name: str,
    enabled: bool,
    host_path: str = _DRI_HOST_PATH,
    mount_path: str = _DRI_MOUNT_PATH,
    volume_name: str = _DRI_VOLUME_NAME,
) -> ReconcileResult:
    """Reconcile hardware device (e.g., /dev/dri) mount on a StatefulSet.

    This function ensures a hardware device is mounted (or unmounted) in a
    Juju-managed StatefulSet for GPU-accelerated transcoding.

    Args:
        manager: K8sResourceManager instance.
        statefulset_name: Name of the StatefulSet (usually self.app.name).
        namespace: Kubernetes namespace (usually self.model.name).
        container_name: Container name from charmcraft.yaml (NOT self.app.name!).
        enabled: Whether hardware transcoding should be enabled.
        host_path: Path on the host to mount (default: /dev/dri).
        mount_path: Path inside the container (default: /dev/dri).
        volume_name: Name for the volume definition.

    Returns:
        ReconcileResult indicating if changes were made.
    """
    from lightkube.types import PatchType

    sts = manager.get(StatefulSet, statefulset_name, namespace)

    if not enabled:
        if not is_hardware_device_mounted(sts, container_name, volume_name):
            return ReconcileResult(changed=False, message="Hardware device not mounted")
        patch_ops = _build_remove_hardware_device_json_patch(sts, container_name, volume_name)
        if patch_ops:
            manager.patch(StatefulSet, statefulset_name, patch_ops, namespace, PatchType.JSON)
        return ReconcileResult(changed=True, message=f"Removed hardware device {volume_name}")

    if is_hardware_device_mounted(sts, container_name, volume_name):
        return ReconcileResult(changed=False, message="Hardware device already mounted")

    patch = _build_hardware_device_patch(container_name, host_path, mount_path, volume_name)
    manager.patch(StatefulSet, statefulset_name, patch, namespace)
    return ReconcileResult(changed=True, message=f"Hardware device mounted at {mount_path}")
