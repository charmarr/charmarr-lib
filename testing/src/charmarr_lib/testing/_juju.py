# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Jubilant integration helpers for Juju testing."""

import json
from typing import TYPE_CHECKING, Any

import jubilant

if TYPE_CHECKING:
    from collections.abc import Sequence


def wait_for_active_idle(
    jujus: "jubilant.Juju | Sequence[jubilant.Juju]",
    timeout: int = 60 * 20,
) -> None:
    """Wait for Juju models to be active and idle without errors.

    Uses jubilant's built-in wait conditions with error checking.

    Args:
        jujus: Single Juju instance or list of instances to wait for.
        timeout: Maximum time to wait in seconds (default: 20 minutes).
    """
    if isinstance(jujus, jubilant.Juju):
        jujus = [jujus]

    for juju in jujus:
        juju.wait(jubilant.all_active, delay=5, successes=3, timeout=timeout)
        juju.wait(jubilant.all_active, delay=5, timeout=60 * 5, error=jubilant.any_error)
        juju.wait(jubilant.all_agents_idle, delay=5, timeout=60 * 5, error=jubilant.any_error)


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


MULTIMETER_CHARM = "charmarr-multimeter-k8s"
MULTIMETER_CHANNEL = "latest/edge"


def deploy_multimeter(
    juju: jubilant.Juju,
    app_name: str = "charmarr-multimeter",
    channel: str = MULTIMETER_CHANNEL,
) -> None:
    """Deploy charmarr-multimeter test utility charm from Charmhub.

    Args:
        juju: Juju instance.
        app_name: Application name for the deployment.
        channel: Charmhub channel to deploy from.
    """
    juju.deploy(
        MULTIMETER_CHARM,
        app_name=app_name,
        channel=channel,
    )
