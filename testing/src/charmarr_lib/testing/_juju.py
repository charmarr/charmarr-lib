# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Jubilant integration helpers for Juju testing."""

import json
import logging
import os
import re
import subprocess
from typing import TYPE_CHECKING, Any

import jubilant

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

MULTIMETER_CHARM = "charmarr-multimeter-k8s"
MULTIMETER_CHANNEL = "latest/edge"


def wait_for_active_idle(
    jujus: "jubilant.Juju | Sequence[jubilant.Juju]",
    timeout: int = 60 * 20,
) -> None:
    """Wait for Juju models to be active and idle.

    Tolerates transient errors during reconciliation - if there's a real
    error, the wait will timeout.

    Args:
        jujus: Single Juju instance or list of instances to wait for.
        timeout: Maximum time to wait in seconds (default: 20 minutes).
    """
    if isinstance(jujus, jubilant.Juju):
        jujus = [jujus]

    for juju in jujus:
        juju.wait(jubilant.all_active, delay=5, successes=3, timeout=timeout)
        juju.wait(jubilant.all_agents_idle, delay=5, timeout=60 * 5)


def get_app_relation_data(
    juju: jubilant.Juju,
    unit: str,
    endpoint: str,
    key: str = "config",
) -> dict[str, Any] | None:
    """Get application relation data from a unit's perspective.

    Retrieves the remote application's data from a relation endpoint.
    Charmarr interfaces use the 'config' key with JSON-encoded Pydantic models.

    Args:
        juju: Juju instance.
        unit: Unit name to query (e.g., "charmarr-multimeter/0").
        endpoint: Relation endpoint name (e.g., "media-storage").
        key: Key in application-data to parse as JSON (default: "config").

    Returns:
        Parsed JSON data from the relation, or None if not found.
    """
    output = juju.cli("show-unit", unit, "--format=json")
    unit_data = json.loads(output)
    relations = unit_data.get(unit, {}).get("relation-info", [])

    for rel in relations:
        if rel.get("endpoint") == endpoint:
            app_data = rel.get("application-data", {})
            if key in app_data:
                return json.loads(app_data[key])

    return None


def deploy_multimeter(
    juju: jubilant.Juju,
    app: str = "charmarr-multimeter",
    channel: str = MULTIMETER_CHANNEL,
    trust: bool = True,
) -> None:
    """Deploy charmarr-multimeter test utility charm from Charmhub.

    Args:
        juju: Juju instance.
        app: Application name for the deployment.
        channel: Charmhub channel to deploy from.
        trust: Whether to grant cluster trust for K8s operations.
    """
    juju.deploy(
        MULTIMETER_CHARM,
        app=app,
        channel=channel,
        trust=trust,
    )


def vpn_creds_available() -> bool:
    """Check if VPN credentials are available in environment."""
    return bool(os.environ.get("WIREGUARD_PRIVATE_KEY"))


def create_vpn_secret(juju: jubilant.Juju, private_key: str) -> str:
    """Create Juju secret with WireGuard private key.

    Args:
        juju: Juju instance.
        private_key: WireGuard private key value.

    Returns:
        Secret URI (e.g., "secret:abcd1234").

    Raises:
        RuntimeError: If secret creation fails.
    """
    output = juju.cli("add-secret", "vpn-key", f"private-key={private_key}")
    match = re.search(r"(secret:\S+)", output)
    if not match:
        raise RuntimeError(f"Failed to parse secret URI from: {output}")
    return match.group(1)


def grant_secret_to_app(juju: jubilant.Juju, secret_name: str, app: str) -> None:
    """Grant a Juju secret to an application.

    Args:
        juju: Juju instance.
        secret_name: Name of the secret to grant.
        app: Application name to grant access to.
    """
    juju.cli("grant-secret", secret_name, app)


def get_node_cidr() -> str:
    """Get node CIDR from environment or discover from Kubernetes.

    Returns a /24 CIDR covering the first node's internal IP.
    Falls back to 10.0.0.0/8 if discovery fails.
    """
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

    logger.warning("Could not discover node IP, using 10.0.0.0/8 as fallback")
    return "10.0.0.0/8"


def assert_app_active(juju: jubilant.Juju, app: str) -> None:
    """Assert that an application is in active status.

    Args:
        juju: Juju instance.
        app: Application name to check.

    Raises:
        AssertionError: If the application is not in active status.
    """
    status = juju.status()
    app_status = status.apps[app]
    assert app_status.app_status.current == "active", (
        f"{app} status: {app_status.app_status.current} - {app_status.app_status.message}"
    )


def ensure_related(
    juju: jubilant.Juju,
    app: str,
    endpoint: str,
    provider_endpoint: str,
) -> None:
    """Ensure an application is related via a specific endpoint.

    Checks if the relation exists first to avoid duplicate integration.
    Waits for active/idle after integrating.

    Args:
        juju: Juju instance.
        app: Requirer application name.
        endpoint: Endpoint name on the requirer app.
        provider_endpoint: Full provider endpoint (e.g., "gluetun:vpn-gateway").
    """
    status = juju.status()
    app_status = status.apps.get(app)
    if app_status and endpoint in app_status.relations:
        return
    juju.integrate(f"{app}:{endpoint}", provider_endpoint)
    wait_for_active_idle(juju)
