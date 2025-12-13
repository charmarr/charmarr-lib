# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for storage volume reconciliation."""

from unittest.mock import MagicMock

import pytest
from lightkube.models.apps_v1 import StatefulSet, StatefulSetSpec
from lightkube.models.core_v1 import (
    Container,
    PersistentVolumeClaimVolumeSource,
    PodSpec,
    PodTemplateSpec,
    Volume,
    VolumeMount,
)
from lightkube.models.meta_v1 import LabelSelector, ObjectMeta

from charmarr_lib.core import (
    K8sResourceManager,
    is_storage_mounted,
    reconcile_storage_volume,
)


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def manager(mock_client):
    return K8sResourceManager(client=mock_client)


def make_statefulset(
    volumes: list | None = None, container_mounts: list | None = None
) -> StatefulSet:
    """Create a StatefulSet with optional volumes and mounts."""
    container = Container(name="radarr", volumeMounts=container_mounts or [])
    return StatefulSet(
        metadata=ObjectMeta(name="radarr", namespace="media"),
        spec=StatefulSetSpec(
            selector=LabelSelector(matchLabels={"app": "radarr"}),
            serviceName="radarr",
            template=PodTemplateSpec(
                spec=PodSpec(
                    containers=[container],
                    volumes=volumes or [],
                )
            ),
        ),
    )


# is_storage_mounted


def test_is_storage_mounted_true_when_both_exist():
    """Returns True when volume and mount both exist."""
    volume = Volume(
        name="charmarr-shared-data",
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName="media-pvc"),
    )
    mount = VolumeMount(name="charmarr-shared-data", mountPath="/data")
    sts = make_statefulset(volumes=[volume], container_mounts=[mount])

    assert is_storage_mounted(sts, "radarr") is True


def test_is_storage_mounted_false_when_no_volume():
    """Returns False when volume doesn't exist."""
    mount = VolumeMount(name="charmarr-shared-data", mountPath="/data")
    sts = make_statefulset(volumes=[], container_mounts=[mount])

    assert is_storage_mounted(sts, "radarr") is False


def test_is_storage_mounted_false_when_no_mount():
    """Returns False when mount doesn't exist."""
    volume = Volume(
        name="charmarr-shared-data",
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName="media-pvc"),
    )
    sts = make_statefulset(volumes=[volume], container_mounts=[])

    assert is_storage_mounted(sts, "radarr") is False


def test_is_storage_mounted_false_when_wrong_container():
    """Returns False when checking wrong container name."""
    volume = Volume(
        name="charmarr-shared-data",
        persistentVolumeClaim=PersistentVolumeClaimVolumeSource(claimName="media-pvc"),
    )
    mount = VolumeMount(name="charmarr-shared-data", mountPath="/data")
    sts = make_statefulset(volumes=[volume], container_mounts=[mount])

    assert is_storage_mounted(sts, "wrong-container") is False


# reconcile_storage_volume


def test_reconcile_patches_when_not_mounted(manager, mock_client):
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


def test_reconcile_skips_when_already_mounted(manager, mock_client):
    """Skips patching when storage already mounted."""
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

    assert result.changed is False
    mock_client.patch.assert_not_called()


def test_reconcile_patch_contains_volume_and_mount(manager, mock_client):
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


def test_reconcile_uses_custom_volume_name(manager, mock_client):
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
