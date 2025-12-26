# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for storage volume reconciliation."""

from lightkube.models.core_v1 import (
    PersistentVolumeClaimVolumeSource,
    PodSecurityContext,
    Volume,
    VolumeMount,
)

from charmarr_lib.core import is_storage_mounted, reconcile_storage_volume

# is_storage_mounted


def test_is_storage_mounted_true_when_both_exist(make_statefulset):
    """Returns True when volume and mount both exist."""
    volume = Volume(
        name="charmarr-shared-data",
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName="media-pvc"),
    )
    mount = VolumeMount(name="charmarr-shared-data", mountPath="/data")
    sts = make_statefulset(volumes=[volume], container_mounts=[mount])

    assert is_storage_mounted(sts, "radarr") is True


def test_is_storage_mounted_false_when_no_volume(make_statefulset):
    """Returns False when volume doesn't exist."""
    mount = VolumeMount(name="charmarr-shared-data", mountPath="/data")
    sts = make_statefulset(volumes=[], container_mounts=[mount])

    assert is_storage_mounted(sts, "radarr") is False


def test_is_storage_mounted_false_when_no_mount(make_statefulset):
    """Returns False when mount doesn't exist."""
    volume = Volume(
        name="charmarr-shared-data",
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName="media-pvc"),
    )
    sts = make_statefulset(volumes=[volume], container_mounts=[])

    assert is_storage_mounted(sts, "radarr") is False


def test_is_storage_mounted_false_when_wrong_container(make_statefulset):
    """Returns False when checking wrong container name."""
    volume = Volume(
        name="charmarr-shared-data",
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName="media-pvc"),
    )
    mount = VolumeMount(name="charmarr-shared-data", mountPath="/data")
    sts = make_statefulset(volumes=[volume], container_mounts=[mount])

    assert is_storage_mounted(sts, "wrong-container") is False


# reconcile_storage_volume


def test_reconcile_patches_when_not_mounted(manager, mock_client, make_statefulset):
    """Patches StatefulSet when storage not mounted."""
    mock_client.get.return_value = make_statefulset()

    result = reconcile_storage_volume(
        manager,
        statefulset_name="radarr",
        namespace="media",
        container_name="radarr",
        pvc_name="charmarr-media",
    )

    assert result.changed is True
    mock_client.patch.assert_called_once()


def test_reconcile_patches_even_when_already_mounted(manager, mock_client, make_statefulset):
    """Strategic merge patch is idempotent, so we always apply it."""
    volume = Volume(
        name="charmarr-shared-data",
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName="charmarr-media"),
    )
    mount = VolumeMount(name="charmarr-shared-data", mountPath="/data")
    mock_client.get.return_value = make_statefulset(volumes=[volume], container_mounts=[mount])

    result = reconcile_storage_volume(
        manager,
        statefulset_name="radarr",
        namespace="media",
        container_name="radarr",
        pvc_name="charmarr-media",
    )

    assert result.changed is True
    mock_client.patch.assert_called_once()


def test_reconcile_patch_contains_volume_and_mount(manager, mock_client, make_statefulset):
    """Patch includes both volume and volumeMount."""
    mock_client.get.return_value = make_statefulset()

    reconcile_storage_volume(
        manager,
        statefulset_name="radarr",
        namespace="media",
        container_name="radarr",
        pvc_name="charmarr-media",
        mount_path="/data",
    )

    patch = mock_client.patch.call_args[0][2]
    volumes = patch["spec"]["template"]["spec"]["volumes"]
    containers = patch["spec"]["template"]["spec"]["containers"]

    assert len(volumes) == 1
    assert volumes[0]["name"] == "charmarr-shared-data"
    assert volumes[0]["persistentVolumeClaim"]["claimName"] == "charmarr-media"

    assert len(containers) == 1
    assert containers[0]["name"] == "radarr"
    assert containers[0]["volumeMounts"][0]["mountPath"] == "/data"


def test_reconcile_uses_custom_volume_name(manager, mock_client, make_statefulset):
    """Supports custom volume name."""
    mock_client.get.return_value = make_statefulset()

    reconcile_storage_volume(
        manager,
        statefulset_name="radarr",
        namespace="media",
        container_name="radarr",
        pvc_name="my-pvc",
        volume_name="custom-volume",
    )

    patch = mock_client.patch.call_args[0][2]
    assert patch["spec"]["template"]["spec"]["volumes"][0]["name"] == "custom-volume"


def test_reconcile_patch_includes_fsgroup(manager, mock_client, make_statefulset):
    """Patch includes fsGroup in SecurityContext when pgid provided."""
    mock_client.get.return_value = make_statefulset()

    reconcile_storage_volume(
        manager,
        statefulset_name="radarr",
        namespace="media",
        container_name="radarr",
        pvc_name="charmarr-media",
        pgid=1000,
    )

    patch = mock_client.patch.call_args[0][2]
    security_context = patch["spec"]["template"]["spec"]["securityContext"]

    assert security_context["fsGroup"] == 1000
    assert "runAsUser" not in security_context
    assert "runAsGroup" not in security_context


def test_reconcile_patch_no_security_context_without_pgid(manager, mock_client, make_statefulset):
    """Patch excludes SecurityContext when pgid not provided."""
    mock_client.get.return_value = make_statefulset()

    reconcile_storage_volume(
        manager,
        statefulset_name="radarr",
        namespace="media",
        container_name="radarr",
        pvc_name="charmarr-media",
    )

    patch = mock_client.patch.call_args[0][2]
    assert "securityContext" not in patch["spec"]["template"]["spec"]


# reconcile_storage_volume - removal (pvc_name=None)


def test_reconcile_removes_when_mounted_and_pvc_none(manager, mock_client, make_statefulset):
    """Removes volume when pvc_name is None and volume is mounted."""
    from lightkube.types import PatchType

    volume = Volume(
        name="charmarr-shared-data",
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName="media-pvc"),
    )
    mount = VolumeMount(name="charmarr-shared-data", mountPath="/data")
    mock_client.get.return_value = make_statefulset(volumes=[volume], container_mounts=[mount])

    result = reconcile_storage_volume(
        manager,
        statefulset_name="radarr",
        namespace="media",
        container_name="radarr",
        pvc_name=None,
    )

    assert result.changed is True
    mock_client.patch.assert_called_once()
    call_kwargs = mock_client.patch.call_args[1]
    assert call_kwargs["patch_type"] == PatchType.JSON


def test_reconcile_skips_removal_when_not_mounted(manager, mock_client, make_statefulset):
    """Skips removal when storage not mounted."""
    mock_client.get.return_value = make_statefulset()

    result = reconcile_storage_volume(
        manager,
        statefulset_name="radarr",
        namespace="media",
        container_name="radarr",
        pvc_name=None,
    )

    assert result.changed is False
    mock_client.patch.assert_not_called()


def test_reconcile_remove_patch_is_json_patch(manager, mock_client, make_statefulset):
    """Removal uses JSON patch with correct operations."""
    volume = Volume(
        name="charmarr-shared-data",
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName="media-pvc"),
    )
    mount = VolumeMount(name="charmarr-shared-data", mountPath="/data")
    mock_client.get.return_value = make_statefulset(volumes=[volume], container_mounts=[mount])

    reconcile_storage_volume(
        manager,
        statefulset_name="radarr",
        namespace="media",
        container_name="radarr",
        pvc_name=None,
    )

    patch_ops = mock_client.patch.call_args[0][2]
    assert isinstance(patch_ops, list)
    assert len(patch_ops) == 2
    assert all(op["op"] == "remove" for op in patch_ops)


def test_reconcile_remove_includes_security_context(manager, mock_client, make_statefulset):
    """Removal also removes securityContext when present."""
    volume = Volume(
        name="charmarr-shared-data",
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName="media-pvc"),
    )
    mount = VolumeMount(name="charmarr-shared-data", mountPath="/data")
    security_context = PodSecurityContext(fsGroup=1000)
    mock_client.get.return_value = make_statefulset(
        volumes=[volume], container_mounts=[mount], security_context=security_context
    )

    reconcile_storage_volume(
        manager,
        statefulset_name="radarr",
        namespace="media",
        container_name="radarr",
        pvc_name=None,
    )

    patch_ops = mock_client.patch.call_args[0][2]
    assert len(patch_ops) == 3
    paths = [op["path"] for op in patch_ops]
    assert "/spec/template/spec/securityContext" in paths
