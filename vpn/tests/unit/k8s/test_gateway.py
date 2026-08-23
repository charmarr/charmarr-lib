# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for gateway StatefulSet patching."""

from unittest.mock import MagicMock

import pytest
from httpx import Response
from lightkube.core.exceptions import ApiError
from lightkube.models.core_v1 import ServiceSpec

from charmarr_lib.vpn import (
    GATEWAY_INIT_CONTAINER_NAME,
    GATEWAY_SIDECAR_CONTAINER_NAME,
    POD_GATEWAY_IMAGE,
    get_cluster_dns_ip,
    reconcile_gateway,
)
from charmarr_lib.vpn._k8s._gateway import (
    _build_patch,  # pyright: ignore[reportPrivateUsage]
)

# _build_patch


def test_build_patch_creates_init_container():
    """Patch includes gateway-init container with correct config."""
    patch = _build_patch("gluetun-gateway-settings", ["10.1.0.0/16"], "abc12345")

    init_containers = patch["spec"]["template"]["spec"]["initContainers"]
    assert len(init_containers) == 1
    assert init_containers[0]["name"] == GATEWAY_INIT_CONTAINER_NAME
    assert init_containers[0]["image"] == POD_GATEWAY_IMAGE
    assert init_containers[0]["securityContext"]["privileged"] is True


def test_build_patch_creates_sidecar_container():
    """Patch includes gateway-sidecar container with correct config."""
    patch = _build_patch("gluetun-gateway-settings", ["10.1.0.0/16"], "abc12345")

    containers = patch["spec"]["template"]["spec"]["containers"]
    assert len(containers) == 1
    assert containers[0]["name"] == GATEWAY_SIDECAR_CONTAINER_NAME
    assert containers[0]["image"] == POD_GATEWAY_IMAGE
    assert containers[0]["securityContext"]["capabilities"]["add"] == ["NET_ADMIN"]


def test_build_patch_includes_volume_mounts():
    """Patch includes volume mounts for ConfigMap on both containers."""
    patch = _build_patch("gluetun-gateway-settings", [], "abc12345")

    init_mounts = patch["spec"]["template"]["spec"]["initContainers"][0]["volumeMounts"]
    assert len(init_mounts) == 1
    assert init_mounts[0]["name"] == "gateway-config"
    assert init_mounts[0]["mountPath"] == "/config"

    sidecar_mounts = patch["spec"]["template"]["spec"]["containers"][0]["volumeMounts"]
    assert len(sidecar_mounts) == 1
    assert sidecar_mounts[0]["name"] == "gateway-config"
    assert sidecar_mounts[0]["mountPath"] == "/config"


def test_build_patch_includes_configmap_volume():
    """Patch includes volume for ConfigMap."""
    patch = _build_patch("gluetun-gateway-settings", [], "abc12345")

    volumes = patch["spec"]["template"]["spec"]["volumes"]
    assert len(volumes) == 1
    assert volumes[0]["name"] == "gateway-config"
    assert volumes[0]["configMap"]["name"] == "gluetun-gateway-settings"


def test_build_patch_includes_iptables_fix():
    """Init container args include iptables rules for input CIDRs."""
    input_cidrs = ["10.1.0.0/16", "192.168.0.0/24"]
    patch = _build_patch("gluetun-gateway-settings", input_cidrs, "abc12345")

    init_args = patch["spec"]["template"]["spec"]["initContainers"][0]["args"]
    assert len(init_args) == 1
    assert "iptables -I INPUT -i eth0 -s 10.1.0.0/16 -j ACCEPT" in init_args[0]
    assert "iptables -I INPUT -i eth0 -s 192.168.0.0/24 -j ACCEPT" in init_args[0]


def test_build_patch_no_iptables_when_empty_cidrs():
    """Init container skips iptables rules when input_cidrs is empty."""
    patch = _build_patch("gluetun-gateway-settings", [], "abc12345")

    init_args = patch["spec"]["template"]["spec"]["initContainers"][0]["args"]
    assert len(init_args) == 1
    assert "iptables" not in init_args[0]
    assert init_args[0] == "/bin/gateway_init.sh"


def test_build_patch_sidecar_has_ports():
    """Sidecar container exposes DHCP and DNS ports."""
    patch = _build_patch("gluetun-gateway-settings", ["10.1.0.0/16"], "abc12345")

    ports = patch["spec"]["template"]["spec"]["containers"][0]["ports"]
    port_names = {p["name"]: p for p in ports}

    assert "dhcp" in port_names
    assert port_names["dhcp"]["containerPort"] == 67
    assert port_names["dhcp"]["protocol"] == "UDP"

    assert "dns" in port_names
    assert port_names["dns"]["containerPort"] == 53


def test_build_patch_includes_config_hash_annotation():
    """Patch includes config hash annotation in pod template metadata."""
    patch = _build_patch("gluetun-gateway-settings", [], "abc12345")

    annotations = patch["spec"]["template"]["metadata"]["annotations"]
    assert "charmarr.io/gateway-config-hash" in annotations
    assert annotations["charmarr.io/gateway-config-hash"] == "abc12345"


# reconcile_gateway


def test_reconcile_gateway_patches_statefulset(manager, mock_client, provider_data):
    """Patches StatefulSet with pod-gateway containers."""
    result = reconcile_gateway(
        manager,
        statefulset_name="gluetun",
        namespace="vpn-gateway",
        data=provider_data,
        input_cidrs=["10.1.0.0/16"],
    )

    assert result.changed is True
    mock_client.patch.assert_called_once()


def test_reconcile_gateway_creates_configmap(manager, mock_client, provider_data):
    """Creates ConfigMap with gateway settings."""
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


def test_reconcile_gateway_returns_message(manager, mock_client, provider_data):
    """Returns descriptive message on success."""
    result = reconcile_gateway(
        manager,
        statefulset_name="gluetun",
        namespace="vpn-gateway",
        data=provider_data,
        input_cidrs=["10.1.0.0/16"],
    )

    assert "gluetun" in result.message
    mock_client.patch.assert_called_once()


# get_cluster_dns_ip


def _not_found() -> ApiError:
    return ApiError(response=Response(404, json={"code": 404, "message": "not found"}))


def _svc(cluster_ip: str | None) -> MagicMock:
    mock_svc = MagicMock()
    mock_svc.spec = ServiceSpec(clusterIP=cluster_ip)
    return mock_svc


def test_get_cluster_dns_ip_returns_cluster_ip(manager, mock_client):
    """Returns the kube-dns service ClusterIP."""
    mock_client.get.return_value = _svc("10.152.183.10")

    result = get_cluster_dns_ip(manager)

    assert result == "10.152.183.10"
    assert mock_client.get.call_args.args[1] == "kube-dns"


def test_get_cluster_dns_ip_falls_back_to_coredns(manager, mock_client):
    """Falls back to coredns when kube-dns is absent (Canonical K8s)."""
    mock_client.get.side_effect = [_not_found(), _svc("10.152.183.249")]

    result = get_cluster_dns_ip(manager)

    assert result == "10.152.183.249"
    assert mock_client.get.call_args.args[1] == "coredns"


def test_get_cluster_dns_ip_raises_when_no_dns_service(manager, mock_client):
    """Raises ValueError when no known DNS service exists."""
    mock_client.get.side_effect = _not_found()

    with pytest.raises(ValueError, match="No cluster DNS service found"):
        get_cluster_dns_ip(manager)


def test_get_cluster_dns_ip_reraises_non_404(manager, mock_client):
    """Propagates API errors other than 404."""
    mock_client.get.side_effect = ApiError(
        response=Response(403, json={"code": 403, "message": "forbidden"})
    )

    with pytest.raises(ApiError):
        get_cluster_dns_ip(manager)


def test_get_cluster_dns_ip_raises_on_no_cluster_ip(manager, mock_client):
    """Raises ValueError when the DNS service has no ClusterIP."""
    mock_client.get.return_value = _svc(None)

    with pytest.raises(ValueError, match="no ClusterIP"):
        get_cluster_dns_ip(manager)
