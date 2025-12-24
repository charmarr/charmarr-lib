# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for gateway client StatefulSet patching."""

from charmarr_lib.vpn import (
    CLIENT_INIT_CONTAINER_NAME,
    CLIENT_SIDECAR_CONTAINER_NAME,
    POD_GATEWAY_IMAGE,
    reconcile_gateway_client,
)
from charmarr_lib.vpn._k8s._gateway_client import (
    _build_configmap_data,  # pyright: ignore[reportPrivateUsage]
    _build_patch,  # pyright: ignore[reportPrivateUsage]
)

# _build_configmap_data


def test_build_configmap_data_creates_settings():
    """Creates settings.sh with correct content."""
    data = _build_configmap_data(
        dns_server_ip="10.152.183.10",
        cluster_cidrs="10.1.0.0/16 10.152.183.0/24",
        vxlan_id=50,
        vxlan_ip_network="172.16.0",
    )

    assert "settings.sh" in data
    assert 'K8S_DNS_IPS="10.152.183.10"' in data["settings.sh"]
    assert 'NOT_ROUTED_TO_GATEWAY_CIDRS="10.1.0.0/16 10.152.183.0/24"' in data["settings.sh"]
    assert 'VXLAN_ID="50"' in data["settings.sh"]
    assert 'VXLAN_IP_NETWORK="172.16.0"' in data["settings.sh"]


# _build_patch


def test_build_patch_creates_init_container(provider_data):
    """Patch includes vpn-route-init container with correct config."""
    patch = _build_patch(provider_data, "vpn-config", "abc12345")

    init_containers = patch["spec"]["template"]["spec"]["initContainers"]
    assert len(init_containers) == 1
    assert init_containers[0]["name"] == CLIENT_INIT_CONTAINER_NAME
    assert init_containers[0]["image"] == POD_GATEWAY_IMAGE
    assert init_containers[0]["securityContext"]["capabilities"]["add"] == ["NET_ADMIN"]


def test_build_patch_creates_sidecar_container(provider_data):
    """Patch includes vpn-route-sidecar container with correct config."""
    patch = _build_patch(provider_data, "vpn-config", "abc12345")

    containers = patch["spec"]["template"]["spec"]["containers"]
    assert len(containers) == 1
    assert containers[0]["name"] == CLIENT_SIDECAR_CONTAINER_NAME
    assert containers[0]["image"] == POD_GATEWAY_IMAGE
    assert containers[0]["securityContext"]["capabilities"]["add"] == ["NET_ADMIN"]


def test_build_patch_includes_gateway_env(provider_data):
    """Containers have gateway env var pointing to gateway DNS name."""
    patch = _build_patch(provider_data, "vpn-config", "abc12345")

    init_env = {
        e["name"]: e["value"]
        for e in patch["spec"]["template"]["spec"]["initContainers"][0]["env"]
    }
    sidecar_env = {
        e["name"]: e["value"] for e in patch["spec"]["template"]["spec"]["containers"][0]["env"]
    }

    assert init_env["gateway"] == "gluetun.vpn-gateway.svc.cluster.local"
    assert sidecar_env["gateway"] == "gluetun.vpn-gateway.svc.cluster.local"


def test_build_patch_includes_configmap_volume(provider_data):
    """Patch includes ConfigMap volume for settings."""
    patch = _build_patch(provider_data, "vpn-config", "abc12345")

    volumes = patch["spec"]["template"]["spec"]["volumes"]
    assert len(volumes) == 1
    assert volumes[0]["configMap"]["name"] == "vpn-config"


def test_build_patch_mounts_config_volume(provider_data):
    """Containers mount the ConfigMap volume at /config."""
    patch = _build_patch(provider_data, "vpn-config", "abc12345")

    init_mounts = patch["spec"]["template"]["spec"]["initContainers"][0]["volumeMounts"]
    sidecar_mounts = patch["spec"]["template"]["spec"]["containers"][0]["volumeMounts"]

    assert len(init_mounts) == 1
    assert init_mounts[0]["mountPath"] == "/config"

    assert len(sidecar_mounts) == 1
    assert sidecar_mounts[0]["mountPath"] == "/config"


def test_build_patch_includes_config_hash_annotation(provider_data):
    """Patch includes config hash annotation in pod template metadata."""
    patch = _build_patch(provider_data, "vpn-config", "abc12345")

    annotations = patch["spec"]["template"]["metadata"]["annotations"]
    assert "charmarr.io/gateway-client-config-hash" in annotations
    assert annotations["charmarr.io/gateway-client-config-hash"] == "abc12345"


# reconcile_gateway_client


def test_reconcile_gateway_client_applies_configmap(manager, mock_client, provider_data):
    """Applies ConfigMap with gateway client settings."""
    reconcile_gateway_client(
        manager,
        statefulset_name="qbittorrent",
        namespace="downloads",
        data=provider_data,
    )

    mock_client.apply.assert_called_once()


def test_reconcile_gateway_client_patches_statefulset(manager, mock_client, provider_data):
    """Patches StatefulSet with gateway client containers."""
    result = reconcile_gateway_client(
        manager,
        statefulset_name="qbittorrent",
        namespace="downloads",
        data=provider_data,
    )

    assert result.changed is True
    mock_client.patch.assert_called_once()


def test_reconcile_gateway_client_returns_message(manager, mock_client, provider_data):
    """Returns descriptive message on success."""
    result = reconcile_gateway_client(
        manager,
        statefulset_name="qbittorrent",
        namespace="downloads",
        data=provider_data,
    )

    assert "qbittorrent" in result.message


def test_reconcile_gateway_client_cleanup_deletes_configmap(manager, mock_client):
    """Deletes ConfigMap when data is None."""
    mock_client.get.return_value = object()

    reconcile_gateway_client(
        manager,
        statefulset_name="qbittorrent",
        namespace="downloads",
        data=None,
    )

    mock_client.delete.assert_called_once()


def test_reconcile_gateway_client_with_killswitch_creates_policy(
    manager, mock_client, provider_data
):
    """Creates NetworkPolicy when killswitch=True."""
    reconcile_gateway_client(
        manager,
        statefulset_name="qbittorrent",
        namespace="downloads",
        data=provider_data,
        killswitch=True,
    )

    assert mock_client.apply.call_count == 2


def test_reconcile_gateway_client_cleanup_with_killswitch_deletes_policy(manager, mock_client):
    """Deletes NetworkPolicy when data is None and killswitch=True."""
    mock_client.get.return_value = object()

    reconcile_gateway_client(
        manager,
        statefulset_name="qbittorrent",
        namespace="downloads",
        data=None,
        killswitch=True,
    )

    assert mock_client.delete.call_count == 2
