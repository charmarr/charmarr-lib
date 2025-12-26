# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Kubernetes resource helpers using multimeter actions."""

import logging
import re
from typing import Any

import jubilant
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ContainerInfo(BaseModel):
    """Container info from a StatefulSet."""

    containers: list[str]
    init_containers: list[str]


def run_multimeter_action(
    juju: jubilant.Juju, action: str, params: dict[str, Any] | None = None
) -> dict[str, str]:
    """Run an action on charmarr-multimeter and return results.

    Args:
        juju: Juju instance.
        action: Action name to run.
        params: Optional action parameters.

    Returns:
        Dict of action results. Empty dict on failure.
    """
    try:
        result = juju.run("charmarr-multimeter/0", action, params or {})
        return dict(result.results)
    except Exception as e:
        logger.warning("Action %s failed: %s", action, e)
        return {}


def get_container_info(juju: jubilant.Juju, namespace: str, name: str) -> ContainerInfo:
    """Get container names from a StatefulSet via multimeter action."""
    results = run_multimeter_action(
        juju, "get-statefulset-containers", {"namespace": namespace, "name": name}
    )
    containers_str = results.get("containers", "")
    init_str = results.get("init-containers", "")
    return ContainerInfo(
        containers=containers_str.split(",") if containers_str else [],
        init_containers=init_str.split(",") if init_str else [],
    )


def get_ingress_ip(juju: jubilant.Juju, app: str = "istio-ingress") -> str | None:
    """Parse IP address from an ingress app's status message.

    Expects status message format: "Serving at X.X.X.X"
    """
    status = juju.status()
    app_status = status.apps.get(app)
    if not app_status:
        logger.warning("App %s not found in status", app)
        return None

    message = app_status.app_status.message or ""
    match = re.search(r"Serving at (\d+\.\d+\.\d+\.\d+)", message)
    if match:
        return match.group(1)

    logger.warning("Could not parse IP from status message: %s", message)
    return None
