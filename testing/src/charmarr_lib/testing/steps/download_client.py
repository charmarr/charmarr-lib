# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Download client relation step definitions."""

import jubilant
from pytest_bdd import parsers, then

from charmarr_lib.testing import get_app_relation_data


@then("the download-client relation should contain api_url")
def relation_has_api_url(juju: jubilant.Juju) -> None:
    """Assert download-client relation contains api_url."""
    data = get_app_relation_data(juju, "charmarr-multimeter/0", "download-client")
    assert data is not None, "No relation data found"
    assert "api_url" in data, f"api_url not in relation data: {data}"


@then("the download-client relation should contain credentials_secret_id")
def relation_has_credentials_secret(juju: jubilant.Juju) -> None:
    """Assert download-client relation contains credentials_secret_id."""
    data = get_app_relation_data(juju, "charmarr-multimeter/0", "download-client")
    assert data is not None, "No relation data found"
    assert "credentials_secret_id" in data, f"credentials_secret_id not in relation data: {data}"


@then("the download-client relation should contain api_key_secret_id")
def relation_has_api_key_secret(juju: jubilant.Juju) -> None:
    """Assert download-client relation contains api_key_secret_id."""
    data = get_app_relation_data(juju, "charmarr-multimeter/0", "download-client")
    assert data is not None, "No relation data found"
    assert "api_key_secret_id" in data, f"api_key_secret_id not in relation data: {data}"


@then(parsers.parse('the download-client relation should contain client type "{expected}"'))
def relation_has_client_type(juju: jubilant.Juju, expected: str) -> None:
    """Assert download-client relation contains expected client type."""
    data = get_app_relation_data(juju, "charmarr-multimeter/0", "download-client")
    assert data is not None, "No relation data found"
    assert data.get("client") == expected, f"Expected client={expected}, got: {data.get('client')}"
