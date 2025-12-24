# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for gateway client StatefulSet patching."""

from lightkube.models.core_v1 import Container

from charmarr_lib.vpn import (
    CLIENT_INIT_CONTAINER_NAME,
    CLIENT_SIDECAR_CONTAINER_NAME,
    POD_GATEWAY_IMAGE,
    build_gateway_client_configmap_data,
    build_gateway_client_patch,
    is_gateway_client_patched,
    reconcile_gateway_client,
    reconcile_gateway_client_configmap,
)

# is_gateway_client_patched


def test_is_gateway_client_patched_true_when_both_exist(make_statefulset):
    """Returns True when init and sidecar containers both exist."""
    init = Container(name=CLIENT_INIT_CONTAINER_NAME, image=POD_GATEWAY_IMAGE)
    sidecar = Container(name=CLIENT_SIDECAR_CONTAINER_NAME, image=POD_GATEWAY_IMAGE)
    sts = make_statefulset(
        name="qbittorrent", namespace="downloads", init_containers=[init], containers=[sidecar]
    )

    assert is_gateway_client_patched(sts) is True


def test_is_gateway_client_patched_false_when_no_init(make_statefulset):
    """Returns False when init container missing."""
    sidecar = Container(name=CLIENT_SIDECAR_CONTAINER_NAME, image=POD_GATEWAY_IMAGE)
    sts = make_statefulset(name="qbittorrent", namespace="downloads", containers=[sidecar])

    assert is_gateway_client_patched(sts) is False


def test_is_gateway_client_patched_false_when_no_sidecar(make_statefulset):
    """Returns False when sidecar container missing."""
    init = Container(name=CLIENT_INIT_CONTAINER_NAME, image=POD_GATEWAY_IMAGE)
    sts = make_statefulset(name="qbittorrent", namespace="downloads", init_containers=[init])

    assert is_gateway_client_patched(sts) is False


def test_is_gateway_client_patched_false_when_empty(make_statefulset):
    """Returns False when no pod-gateway containers."""
    sts = make_statefulset(name="qbittorrent", namespace="downloads")

    assert is_gateway_client_patched(sts) is False


# build_gateway_client_configmap_data


def test_build_gateway_client_configmap_data_creates_settings():
    """Creates settings.sh with correct content."""
    data = build_gateway_client_configmap_data(
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


# build_gateway_client_patch


def test_build_gateway_client_patch_creates_init_container(provider_data):
    """Patch includes vpn-route-init container with correct config."""
    patch = build_gateway_client_patch(provider_data, "vpn-config", "abc12345")

    init_containers = patch["spec"]["template"]["spec"]["initContainers"]
    assert len(init_containers) == 1
    assert init_containers[0]["name"] == CLIENT_INIT_CONTAINER_NAME
    assert init_containers[0]["image"] == POD_GATEWAY_IMAGE
    assert init_containers[0]["securityContext"]["capabilities"]["add"] == ["NET_ADMIN"]


def test_build_gateway_client_patch_creates_sidecar_container(provider_data):
    """Patch includes vpn-route-sidecar container with correct config."""
    patch = build_gateway_client_patch(provider_data, "vpn-config", "abc12345")

    containers = patch["spec"]["template"]["spec"]["containers"]
    assert len(containers) == 1
    assert containers[0]["name"] == CLIENT_SIDECAR_CONTAINER_NAME
    assert containers[0]["image"] == POD_GATEWAY_IMAGE
    assert containers[0]["securityContext"]["capabilities"]["add"] == ["NET_ADMIN"]


def test_build_gateway_client_patch_includes_gateway_env(provider_data):
    """Containers have gateway env var pointing to gateway DNS name."""
    patch = build_gateway_client_patch(provider_data, "vpn-config", "abc12345")

    init_env = {
        e["name"]: e["value"]
        for e in patch["spec"]["template"]["spec"]["initContainers"][0]["env"]
    }
    sidecar_env = {
        e["name"]: e["value"] for e in patch["spec"]["template"]["spec"]["containers"][0]["env"]
    }

    assert init_env["gateway"] == "gluetun.vpn-gateway.svc.cluster.local"
    assert sidecar_env["gateway"] == "gluetun.vpn-gateway.svc.cluster.local"


def test_build_gateway_client_patch_includes_configmap_volume(provider_data):
    """Patch includes ConfigMap volume for settings."""
    patch = build_gateway_client_patch(provider_data, "vpn-config", "abc12345")

    volumes = patch["spec"]["template"]["spec"]["volumes"]
    assert len(volumes) == 1
    assert volumes[0]["configMap"]["name"] == "vpn-config"


def test_build_gateway_client_patch_mounts_config_volume(provider_data):
    """Containers mount the ConfigMap volume at /config."""
    patch = build_gateway_client_patch(provider_data, "vpn-config", "abc12345")

    init_mounts = patch["spec"]["template"]["spec"]["initContainers"][0]["volumeMounts"]
    sidecar_mounts = patch["spec"]["template"]["spec"]["containers"][0]["volumeMounts"]

    assert len(init_mounts) == 1
    assert init_mounts[0]["mountPath"] == "/config"

    assert len(sidecar_mounts) == 1
    assert sidecar_mounts[0]["mountPath"] == "/config"


def test_build_gateway_client_patch_includes_config_hash_annotation(provider_data):
    """Patch includes config hash annotation in pod template metadata."""
    patch = build_gateway_client_patch(provider_data, "vpn-config", "abc12345")

    annotations = patch["spec"]["template"]["metadata"]["annotations"]
    assert "charmarr.io/gateway-client-config-hash" in annotations
    assert annotations["charmarr.io/gateway-client-config-hash"] == "abc12345"


# reconcile_gateway_client


def test_reconcile_gateway_client_patches_statefulset(manager, mock_client, provider_data):
    """Patches StatefulSet with gateway client containers."""
    result = reconcile_gateway_client(
        manager,
        statefulset_name="qbittorrent",
        namespace="downloads",
        data=provider_data,
        configmap_name="vpn-config",
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
        configmap_name="vpn-config",
    )

    assert "qbittorrent" in result.message


# reconcile_gateway_client_configmap


def test_reconcile_gateway_client_configmap_applies(manager, mock_client):
    """Applies ConfigMap via server-side apply."""
    result = reconcile_gateway_client_configmap(
        manager,
        configmap_name="vpn-settings",
        namespace="downloads",
        dns_server_ip="10.152.183.10",
        cluster_cidrs="10.1.0.0/16 10.152.183.0/24",
        vxlan_id=50,
        vxlan_ip_network="172.16.0",
    )

    assert result.changed is True
    assert "Reconciled" in result.message
    mock_client.apply.assert_called_once()
