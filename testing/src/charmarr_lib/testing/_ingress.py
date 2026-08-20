# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Ingress discovery helpers shared by traefik and istio-ingress tests."""

import logging
import re

import jubilant

from charmarr_lib.testing._juju import get_app_relation_data

logger = logging.getLogger(__name__)

# istio-ingress-k8s reports "Serving at 10.0.0.1", traefik-k8s reports
# "Serving at http://10.0.0.1", so the scheme has to be optional.
_SERVING_AT = re.compile(r"Serving at (?:https?://)?(\d+\.\d+\.\d+\.\d+)")


def get_ingress_ip(juju: jubilant.Juju, app: str = "traefik") -> str | None:
    """Parse the external IP address from an ingress app's status message."""
    status = juju.status()
    app_status = status.apps.get(app)
    if not app_status:
        logger.warning("App %s not found in status", app)
        return None

    message = app_status.app_status.message or ""
    match = _SERVING_AT.search(message)
    if match:
        return match.group(1)

    logger.warning("Could not parse IP from status message: %s", message)
    return None


def get_ingress_url(juju: jubilant.Juju, app: str) -> str | None:
    """Read the external URL an ingress provider published to a requirer app.

    This is the ground truth for path-routed providers such as traefik, which
    choose the prefix themselves rather than taking it from charm config.
    """
    data = get_app_relation_data(juju, f"{app}/0", "ingress", key="ingress")
    if not data:
        logger.warning("No ingress relation data found for %s", app)
        return None
    return str(data["url"]).rstrip("/")
