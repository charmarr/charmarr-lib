# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Arr family shared step definitions."""

import json

import jubilant
from pytest_bdd import given, parsers, then

from charmarr_lib.testing import wait_for_active_idle


@given(parsers.parse("{requirer} is related to {provider} via media-indexer"))
def relate_via_media_indexer(juju: jubilant.Juju, requirer: str, provider: str) -> None:
    """Integrate requirer with provider via media-indexer relation."""
    status = juju.status()
    app_status = status.apps.get(requirer)
    if app_status and "media-indexer" in app_status.relations:
        return
    juju.integrate(f"{requirer}:media-indexer", f"{provider}:media-indexer")
    wait_for_active_idle(juju)


@then(parsers.parse("the {app} charm should be active"))
def charm_should_be_active(juju: jubilant.Juju, app: str) -> None:
    """Assert a charm is active."""
    status = juju.status()
    app_status = status.apps[app]
    assert app_status.app_status.current == "active", (
        f"{app} status: {app_status.app_status.current} - {app_status.app_status.message}"
    )


@then(parsers.parse("an api-key secret should exist for {app}"))
def api_key_secret_exists(juju: jubilant.Juju, app: str) -> None:
    """Assert an api-key secret exists for the app."""
    output = juju.cli("list-secrets", "--format=json")
    secrets = json.loads(output)

    found = False
    for _, info in secrets.items():
        if info.get("owner") == app and info.get("label") == "api-key":
            found = True
            break

    assert found, f"No api-key secret found for {app}"
