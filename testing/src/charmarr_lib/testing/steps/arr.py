# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Arr family shared step definitions."""

import json
import os
from typing import Any
from urllib.parse import urlparse

import jubilant
from pytest_bdd import given, parsers, then, when

from charmarr_lib.testing import (
    ArrCredentials,
    assert_app_active,
    ensure_related,
    http_from_unit,
    wait_for_active_idle,
)

SABNZBD_CHANNEL = os.environ.get("CHARMARR_SABNZBD_CHANNEL", "latest/edge")


def _local_url(credentials: ArrCredentials, path: str) -> str:
    """Convert base_url to localhost URL for exec from unit."""
    parsed = urlparse(credentials.base_url)
    port = parsed.port or 80
    url_base = parsed.path.rstrip("/")
    return f"http://localhost:{port}{url_base}{path}"


@given(parsers.parse("{requirer} is related to {provider} via media-indexer"))
def relate_via_media_indexer(juju: jubilant.Juju, requirer: str, provider: str) -> None:
    """Integrate requirer with provider via media-indexer relation."""
    ensure_related(juju, requirer, "media-indexer", f"{provider}:media-indexer")


@given(parsers.parse("{requirer} is related to {provider} via download-client"))
def relate_via_download_client(juju: jubilant.Juju, requirer: str, provider: str) -> None:
    """Integrate requirer with provider via download-client relation."""
    ensure_related(juju, requirer, "download-client", f"{provider}:download-client")


@given("sabnzbd is deployed", target_fixture="sabnzbd_deployed")
def sabnzbd_is_deployed(juju: jubilant.Juju, storage_deployed: None) -> None:
    """Deploy sabnzbd from Charmhub."""
    status = juju.status()
    if "sabnzbd" in status.apps:
        return
    juju.deploy(
        "sabnzbd-k8s",
        app="sabnzbd",
        channel=SABNZBD_CHANNEL,
        trust=True,
        config={"unsafe-mode": "true"},
    )
    juju.integrate("sabnzbd:media-storage", "charmarr-storage:media-storage")
    wait_for_active_idle(juju)


@when(parsers.parse("recyclarr config action is run on {app}"))
def run_recyclarr_action(juju: jubilant.Juju, app: str) -> None:
    """Run recyclarr sync action on an arr app."""
    juju.run(f"{app}/0", "sync-trash-profiles")


@then(parsers.parse("the {app} charm should be active"))
def charm_should_be_active(juju: jubilant.Juju, app: str) -> None:
    """Assert a charm is active."""
    assert_app_active(juju, app)


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


@then(parsers.parse("{app} API should return system status"))
def arr_api_returns_status(juju: jubilant.Juju, app: str, credentials: ArrCredentials) -> None:
    """Verify arr API is accessible and returns system status."""
    url = _local_url(credentials, "/api/v3/system/status")
    response = http_from_unit(juju, f"{app}/0", url, headers={"X-Api-Key": credentials.api_key})
    assert response.status_code == 200
    data = response.json_body()
    assert "appName" in data


@then(parsers.parse("{app} should have sabnzbd registered as download client"))
def arr_has_sabnzbd_download_client(
    juju: jubilant.Juju, app: str, credentials: ArrCredentials
) -> None:
    """Verify sabnzbd is registered as download client."""
    url = _local_url(credentials, "/api/v3/downloadclient")
    response = http_from_unit(juju, f"{app}/0", url, headers={"X-Api-Key": credentials.api_key})
    assert response.status_code == 200
    clients: list[dict[str, Any]] = response.json_body()
    sabnzbd_clients = [c for c in clients if c.get("implementation") == "Sabnzbd"]
    assert len(sabnzbd_clients) > 0, f"No SABnzbd download client found in {app}"


@then(parsers.parse("{app} should have quality profiles configured"))
def arr_has_quality_profiles(juju: jubilant.Juju, app: str, credentials: ArrCredentials) -> None:
    """Verify arr has quality profiles from recyclarr."""
    url = _local_url(credentials, "/api/v3/qualityprofile")
    response = http_from_unit(juju, f"{app}/0", url, headers={"X-Api-Key": credentials.api_key})
    assert response.status_code == 200
    profiles: list[dict[str, Any]] = response.json_body()
    assert len(profiles) > 0, f"No quality profiles found in {app}"
