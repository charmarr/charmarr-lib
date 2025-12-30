# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Multimeter deployment step definitions."""

import jubilant
from pytest_bdd import given, parsers, then

from charmarr_lib.testing import assert_app_active, deploy_multimeter, wait_for_active_idle


@given("the charmarr-multimeter charm is deployed")
def deploy_multimeter_step(juju: jubilant.Juju) -> None:
    """Deploy charmarr-multimeter from Charmhub."""
    status = juju.status()
    if "charmarr-multimeter" not in status.apps:
        deploy_multimeter(juju)
        wait_for_active_idle(juju)


@given(parsers.parse("charmarr-multimeter is related to {app} via download-client"))
def relate_multimeter_download_client(juju: jubilant.Juju, app: str) -> None:
    """Integrate charmarr-multimeter with an app via download-client relation."""
    status = juju.status()
    multimeter = status.apps.get("charmarr-multimeter")
    if multimeter and "download-client" in multimeter.relations:
        return
    juju.integrate("charmarr-multimeter:download-client", f"{app}:download-client")
    wait_for_active_idle(juju)


@then("the multimeter charm should be active")
def multimeter_active(juju: jubilant.Juju) -> None:
    """Assert multimeter charm is active."""
    assert_app_active(juju, "charmarr-multimeter")
