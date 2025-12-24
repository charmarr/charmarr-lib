# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for gateway StatefulSet patching."""

from unittest.mock import MagicMock

import pytest
from lightkube.models.core_v1 import Container, ServiceSpec

from charmarr_lib.vpn import (
    GATEWAY_INIT_CONTAINER_NAME,
    GATEWAY_SIDECAR_CONTAINER_NAME,
    POD_GATEWAY_IMAGE,
    build_gateway_patch,
    get_cluster_dns_ip,
    is_gateway_patched,
    reconcile_gateway,
)

# is_gateway_patched


def test_is_gateway_patched_true_when_both_exist(make_statefulset):
    """Returns True when init and sidecar containers both exist."""
    init = Container(name=GATEWAY_INIT_CONTAINER_NAME, image=POD_GATEWAY_IMAGE)
    sidecar = Container(name=GATEWAY_SIDECAR_CONTAINER_NAME, image=POD_GATEWAY_IMAGE)
    sts = make_statefulset(init_containers=[init], containers=[sidecar])

    assert is_gateway_patched(sts) is True


def test_is_gateway_patched_false_when_no_init(make_statefulset):
    """Returns False when init container missing."""
    sidecar = Container(name=GATEWAY_SIDECAR_CONTAINER_NAME, image=POD_GATEWAY_IMAGE)
    sts = make_statefulset(containers=[sidecar])

    assert is_gateway_patched(sts) is False


def test_is_gateway_patched_false_when_no_sidecar(make_statefulset):
    """Returns False when sidecar container missing."""
    init = Container(name=GATEWAY_INIT_CONTAINER_NAME, image=POD_GATEWAY_IMAGE)
    sts = make_statefulset(init_containers=[init])

    assert is_gateway_patched(sts) is False


def test_is_gateway_patched_false_when_empty(make_statefulset):
    """Returns False when no pod-gateway containers."""
    sts = make_statefulset()

    assert is_gateway_patched(sts) is False


# build_gateway_patch


def test_build_gateway_patch_creates_init_container():
    """Patch includes gateway-init container with correct config."""
    patch = build_gateway_patch("gluetun-gateway-settings", ["10.1.0.0/16"])

    init_containers = patch["spec"]["template"]["spec"]["initContainers"]
    assert len(init_containers) == 1
    assert init_containers[0]["name"] == GATEWAY_INIT_CONTAINER_NAME
    assert init_containers[0]["image"] == POD_GATEWAY_IMAGE
    assert init_containers[0]["securityContext"]["privileged"] is True


def test_build_gateway_patch_creates_sidecar_container():
    """Patch includes gateway-sidecar container with correct config."""
    patch = build_gateway_patch("gluetun-gateway-settings", ["10.1.0.0/16"])

    containers = patch["spec"]["template"]["spec"]["containers"]
    assert len(containers) == 1
    assert containers[0]["name"] == GATEWAY_SIDECAR_CONTAINER_NAME
    assert containers[0]["image"] == POD_GATEWAY_IMAGE
    assert containers[0]["securityContext"]["capabilities"]["add"] == ["NET_ADMIN"]


def test_build_gateway_patch_includes_volume_mounts():
    """Patch includes volume mounts for ConfigMap on both containers."""
    patch = build_gateway_patch("gluetun-gateway-settings", [])

    init_mounts = patch["spec"]["template"]["spec"]["initContainers"][0]["volumeMounts"]
    assert len(init_mounts) == 1
    assert init_mounts[0]["name"] == "gateway-config"
    assert init_mounts[0]["mountPath"] == "/config"

    sidecar_mounts = patch["spec"]["template"]["spec"]["containers"][0]["volumeMounts"]
    assert len(sidecar_mounts) == 1
    assert sidecar_mounts[0]["name"] == "gateway-config"
    assert sidecar_mounts[0]["mountPath"] == "/config"


def test_build_gateway_patch_includes_configmap_volume():
    """Patch includes volume for ConfigMap."""
    patch = build_gateway_patch("gluetun-gateway-settings", [])

    volumes = patch["spec"]["template"]["spec"]["volumes"]
    assert len(volumes) == 1
    assert volumes[0]["name"] == "gateway-config"
    assert volumes[0]["configMap"]["name"] == "gluetun-gateway-settings"


def test_build_gateway_patch_includes_iptables_fix():
    """Init container args include iptables rules for input CIDRs."""
    input_cidrs = ["10.1.0.0/16", "192.168.0.0/24"]
    patch = build_gateway_patch("gluetun-gateway-settings", input_cidrs)

    init_args = patch["spec"]["template"]["spec"]["initContainers"][0]["args"]
    assert len(init_args) == 1
    assert "iptables -I INPUT -i eth0 -s 10.1.0.0/16 -j ACCEPT" in init_args[0]
    assert "iptables -I INPUT -i eth0 -s 192.168.0.0/24 -j ACCEPT" in init_args[0]


def test_build_gateway_patch_no_iptables_when_empty_cidrs():
    """Init container skips iptables rules when input_cidrs is empty."""
    patch = build_gateway_patch("gluetun-gateway-settings", [])

    init_args = patch["spec"]["template"]["spec"]["initContainers"][0]["args"]
    assert len(init_args) == 1
    assert "iptables" not in init_args[0]
    assert init_args[0] == "/bin/gateway_init.sh"


def test_build_gateway_patch_sidecar_has_ports():
    """Sidecar container exposes DHCP and DNS ports."""
    patch = build_gateway_patch("gluetun-gateway-settings", ["10.1.0.0/16"])

    ports = patch["spec"]["template"]["spec"]["containers"][0]["ports"]
    port_names = {p["name"]: p for p in ports}

    assert "dhcp" in port_names
    assert port_names["dhcp"]["containerPort"] == 67
    assert port_names["dhcp"]["protocol"] == "UDP"

    assert "dns" in port_names
    assert port_names["dns"]["containerPort"] == 53


# reconcile_gateway


def test_reconcile_gateway_patches_when_not_patched(
    manager, mock_client, provider_data, make_statefulset
):
    """Patches StatefulSet when gateway containers not present."""
    mock_client.get.return_value = make_statefulset()

    result = reconcile_gateway(
        manager,
        statefulset_name="gluetun",
        namespace="vpn-gateway",
        data=provider_data,
        input_cidrs=["10.1.0.0/16"],
    )

    assert result.changed is True
    mock_client.patch.assert_called_once()


def test_reconcile_gateway_creates_configmap(
    manager, mock_client, provider_data, make_statefulset
):
    """Creates ConfigMap with gateway settings."""
    mock_client.get.return_value = make_statefulset()

    reconcile_gateway(
        manager,
        statefulset_name="gluetun",
        namespace="vpn-gateway",
        data=provider_data,
        input_cidrs=[],
    )

    mock_client.apply.assert_called_once()
    configmap = mock_client.apply.call_args[0][0]
    assert configmap.metadata.name == "gluetun-gateway-settings"
    assert configmap.metadata.namespace == "vpn-gateway"
    assert "settings.sh" in configmap.data
    assert 'VXLAN_ID="42"' in configmap.data["settings.sh"]


def test_reconcile_gateway_updates_when_already_patched(
    manager, mock_client, provider_data, make_statefulset
):
    """Re-applies patch when gateway containers already present."""
    init = Container(name=GATEWAY_INIT_CONTAINER_NAME, image=POD_GATEWAY_IMAGE)
    sidecar = Container(name=GATEWAY_SIDECAR_CONTAINER_NAME, image=POD_GATEWAY_IMAGE)
    mock_client.get.return_value = make_statefulset(init_containers=[init], containers=[sidecar])

    result = reconcile_gateway(
        manager,
        statefulset_name="gluetun",
        namespace="vpn-gateway",
        data=provider_data,
        input_cidrs=["10.1.0.0/16"],
    )

    assert result.changed is True
    assert "Updated" in result.message
    mock_client.patch.assert_called_once()


def test_reconcile_gateway_returns_message(manager, mock_client, provider_data, make_statefulset):
    """Returns descriptive message on success."""
    mock_client.get.return_value = make_statefulset()

    result = reconcile_gateway(
        manager,
        statefulset_name="gluetun",
        namespace="vpn-gateway",
        data=provider_data,
        input_cidrs=["10.1.0.0/16"],
    )

    assert "gluetun" in result.message


# get_cluster_dns_ip


def test_get_cluster_dns_ip_returns_cluster_ip(manager, mock_client):
    """Returns the kube-dns service ClusterIP."""
    mock_svc = MagicMock()
    mock_svc.spec = ServiceSpec(clusterIP="10.152.183.10")
    mock_client.get.return_value = mock_svc

    result = get_cluster_dns_ip(manager)

    assert result == "10.152.183.10"
    mock_client.get.assert_called_once()


def test_get_cluster_dns_ip_raises_on_no_cluster_ip(manager, mock_client):
    """Raises ValueError when kube-dns has no ClusterIP."""
    mock_svc = MagicMock()
    mock_svc.spec = ServiceSpec(clusterIP=None)
    mock_client.get.return_value = mock_svc

    with pytest.raises(ValueError, match="no ClusterIP"):
        get_cluster_dns_ip(manager)
