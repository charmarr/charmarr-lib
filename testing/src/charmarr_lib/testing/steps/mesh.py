# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Istio service mesh deployment step definitions."""

import os

import jubilant
from pytest_bdd import given, parsers

from charmarr_lib.testing import ensure_related, wait_for_active_idle

ISTIO_CHANNEL = os.environ.get("CHARMARR_ISTIO_CHANNEL", "2/edge")


@given("istio-k8s is deployed")
def deploy_istio(juju: jubilant.Juju) -> None:
    """Deploy istio-k8s from Charmhub."""
    status = juju.status()
    if "istio-k8s" in status.apps:
        return
    juju.deploy("istio-k8s", app="istio-k8s", channel=ISTIO_CHANNEL, trust=True)
    wait_for_active_idle(juju)


@given("istio-beacon is deployed")
def deploy_istio_beacon(juju: jubilant.Juju) -> None:
    """Deploy istio-beacon-k8s from Charmhub."""
    status = juju.status()
    if "istio-beacon" in status.apps:
        return
    juju.deploy("istio-beacon-k8s", app="istio-beacon", channel=ISTIO_CHANNEL, trust=True)
    wait_for_active_idle(juju)


@given("istio-ingress is deployed")
def deploy_istio_ingress(juju: jubilant.Juju) -> None:
    """Deploy istio-ingress-k8s from Charmhub."""
    status = juju.status()
    if "istio-ingress" in status.apps:
        return
    juju.deploy("istio-ingress-k8s", app="istio-ingress", channel=ISTIO_CHANNEL, trust=True)
    wait_for_active_idle(juju)


@given(parsers.parse("{app} is related to istio-beacon via service-mesh"))
def relate_app_to_mesh(juju: jubilant.Juju, app: str) -> None:
    """Integrate an app with istio-beacon via service-mesh relation."""
    ensure_related(juju, app, "service-mesh", "istio-beacon:service-mesh")


@given(parsers.parse("{app} is related to istio-ingress via istio-ingress-route"))
def relate_app_to_ingress(juju: jubilant.Juju, app: str) -> None:
    """Integrate an app with istio-ingress via istio-ingress-route relation."""
    ensure_related(juju, app, "istio-ingress-route", "istio-ingress:istio-ingress-route")
