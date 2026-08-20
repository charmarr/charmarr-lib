# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Traefik ingress deployment step definitions."""

import os

import jubilant
from pytest_bdd import given, parsers

from charmarr_lib.testing import wait_for_app_status

TRAEFIK_CHANNEL = os.environ.get("CHARMARR_TRAEFIK_CHANNEL", "latest/stable")


@given("traefik is deployed")
def deploy_traefik(juju: jubilant.Juju) -> None:
    """Deploy traefik-k8s from Charmhub."""
    status = juju.status()
    if "traefik" in status.apps:
        return
    juju.deploy("traefik-k8s", app="traefik", channel=TRAEFIK_CHANNEL, trust=True)
    wait_for_app_status(juju, "traefik", "active")


@given(parsers.parse("{app} is related to traefik via ingress"))
def relate_app_to_traefik(juju: jubilant.Juju, app: str) -> None:
    """Integrate an app with traefik via the generic ingress relation."""
    status = juju.status()
    app_status = status.apps.get(app)
    if app_status and "ingress" in app_status.relations:
        return
    juju.integrate(f"{app}:ingress", "traefik:ingress")
    wait_for_app_status(juju, "traefik", "active")
    juju.wait(jubilant.all_agents_idle, delay=5, timeout=60 * 10)
