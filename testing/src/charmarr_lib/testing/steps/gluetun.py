# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Gluetun VPN gateway deployment step definitions."""

import os
import re
import subprocess

import jubilant
from pytest_bdd import given, parsers, then

from charmarr_lib.testing import wait_for_active_idle

GLUETUN_CHARM = "gluetun-k8s"
GLUETUN_CHANNEL = os.environ.get("CHARMARR_GLUETUN_CHANNEL", "latest/edge")

POD_CIDR = "10.1.0.0/16"
SERVICE_CIDR = "10.152.183.0/24"


def _get_node_cidr() -> str:
    """Get node CIDR from environment or discover from Kubernetes."""
    if cidr := os.environ.get("NODE_CIDR"):
        return cidr
    try:
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "nodes",
                "-o",
                "jsonpath={.items[0].status.addresses[?(@.type=='InternalIP')].address}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        node_ip = result.stdout.strip()
        if node_ip:
            octets = node_ip.split(".")
            return f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"
    except Exception:
        pass
    return "10.0.0.0/8"


def _create_vpn_secret(juju: jubilant.Juju, private_key: str) -> str:
    """Create Juju secret with WireGuard private key. Returns the secret URI."""
    output = juju.cli("add-secret", "vpn-key", f"private-key={private_key}")
    match = re.search(r"(secret:\S+)", output)
    if not match:
        raise RuntimeError(f"Failed to parse secret URI from: {output}")
    return match.group(1)


@given("gluetun is deployed with valid VPN config")
def deploy_gluetun(juju: jubilant.Juju) -> None:
    """Deploy gluetun with VPN configuration from environment."""
    status = juju.status()
    if "gluetun" in status.apps:
        return

    private_key = os.environ.get("WIREGUARD_PRIVATE_KEY", "")
    if not private_key:
        raise RuntimeError("WIREGUARD_PRIVATE_KEY environment variable required")

    secret_uri = _create_vpn_secret(juju, private_key)

    node_cidr = _get_node_cidr()
    cluster_cidrs = f"{POD_CIDR},{SERVICE_CIDR},{node_cidr}"

    config = {
        "vpn-provider": "protonvpn",
        "cluster-cidrs": cluster_cidrs,
        "wireguard-private-key-secret": secret_uri,
    }
    juju.deploy(GLUETUN_CHARM, app="gluetun", channel=GLUETUN_CHANNEL, trust=True, config=config)
    juju.cli("grant-secret", "vpn-key", "gluetun")
    wait_for_active_idle(juju)


@then("the gluetun charm should be active")
def gluetun_active(juju: jubilant.Juju) -> None:
    """Assert gluetun charm is active."""
    status = juju.status()
    app = status.apps["gluetun"]
    assert app.app_status.current == "active", (
        f"Gluetun status: {app.app_status.current} - {app.app_status.message}"
    )


@then(parsers.parse('the {app} StatefulSet should have init container "{container}"'))
def statefulset_has_init_container(juju: jubilant.Juju, app: str, container: str) -> None:
    """Assert StatefulSet has the specified init container."""
    from charmarr_lib.testing import get_container_info

    assert juju.model is not None, "Juju model not set"
    info = get_container_info(juju, juju.model, app)
    assert container in info.init_containers, (
        f"Expected init container {container}, found: {info.init_containers}"
    )


@then(parsers.parse('the {app} StatefulSet should have container "{container}"'))
def statefulset_has_container(juju: jubilant.Juju, app: str, container: str) -> None:
    """Assert StatefulSet has the specified container."""
    from charmarr_lib.testing import get_container_info

    assert juju.model is not None, "Juju model not set"
    info = get_container_info(juju, juju.model, app)
    assert container in info.containers, (
        f"Expected container {container}, found: {info.containers}"
    )
