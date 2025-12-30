# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Gluetun VPN gateway deployment step definitions."""

import os

import jubilant
from pytest_bdd import given, parsers, then

from charmarr_lib.testing import (
    assert_app_active,
    create_vpn_secret,
    ensure_related,
    get_container_info,
    get_node_cidr,
    grant_secret_to_app,
    wait_for_active_idle,
)

GLUETUN_CHARM = "gluetun-k8s"
GLUETUN_CHANNEL = os.environ.get("CHARMARR_GLUETUN_CHANNEL", "latest/edge")

POD_CIDR = "10.1.0.0/16"
SERVICE_CIDR = "10.152.183.0/24"


@given("gluetun is deployed with valid VPN config")
def deploy_gluetun(juju: jubilant.Juju) -> None:
    """Deploy gluetun with VPN configuration from environment."""
    status = juju.status()
    if "gluetun" in status.apps:
        return

    private_key = os.environ.get("WIREGUARD_PRIVATE_KEY", "")
    if not private_key:
        raise RuntimeError("WIREGUARD_PRIVATE_KEY environment variable required")

    secret_uri = create_vpn_secret(juju, private_key)

    node_cidr = get_node_cidr()
    cluster_cidrs = f"{POD_CIDR},{SERVICE_CIDR},{node_cidr}"

    config = {
        "vpn-provider": "protonvpn",
        "cluster-cidrs": cluster_cidrs,
        "wireguard-private-key-secret": secret_uri,
    }
    juju.deploy(GLUETUN_CHARM, app="gluetun", channel=GLUETUN_CHANNEL, trust=True, config=config)
    grant_secret_to_app(juju, "vpn-key", "gluetun")
    wait_for_active_idle(juju)


@given(parsers.parse("{app} is related to gluetun via vpn-gateway"))
def relate_app_to_gluetun(juju: jubilant.Juju, app: str) -> None:
    """Integrate an app with gluetun via vpn-gateway relation."""
    ensure_related(juju, app, "vpn-gateway", "gluetun:vpn-gateway")


@then("the gluetun charm should be active")
def gluetun_active(juju: jubilant.Juju) -> None:
    """Assert gluetun charm is active."""
    assert_app_active(juju, "gluetun")


@then(parsers.parse('the {app} StatefulSet should have init container "{container}"'))
def statefulset_has_init_container(juju: jubilant.Juju, app: str, container: str) -> None:
    """Assert StatefulSet has the specified init container."""
    assert juju.model is not None, "Juju model not set"
    info = get_container_info(juju, juju.model, app)
    assert container in info.init_containers, (
        f"Expected init container {container}, found: {info.init_containers}"
    )


@then(parsers.parse('the {app} StatefulSet should have container "{container}"'))
def statefulset_has_container(juju: jubilant.Juju, app: str, container: str) -> None:
    """Assert StatefulSet has the specified container."""
    assert juju.model is not None, "Juju model not set"
    info = get_container_info(juju, juju.model, app)
    assert container in info.containers, (
        f"Expected container {container}, found: {info.containers}"
    )
