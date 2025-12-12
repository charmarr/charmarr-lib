# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for ProwlarrApiClient."""

import pytest
from pytest_httpx import HTTPXMock

from charmarr_lib.core import ProwlarrApiClient

APPLICATION = {
    "id": 1,
    "name": "Radarr",
    "syncLevel": "fullSync",
    "implementation": "Radarr",
    "configContract": "RadarrSettings",
}
INDEXER = {
    "id": 1,
    "name": "NZBgeek",
    "enable": True,
    "protocol": "usenet",
    "implementation": "Newznab",
}
HOST_CONFIG = {"id": 1, "bindAddress": "*", "port": 9696, "urlBase": None}


@pytest.fixture
def client():
    return ProwlarrApiClient(
        base_url="http://localhost:9696",
        api_key="test-api-key",
        max_retries=1,
    )


def test_uses_v1_api_path(client: ProwlarrApiClient, httpx_mock: HTTPXMock):
    """ProwlarrApiClient uses /api/v1/ path prefix."""
    httpx_mock.add_response(json=[])
    client.get_applications()

    request = httpx_mock.get_request()
    assert request is not None
    assert "/api/v1/" in str(request.url)


def test_get_applications_endpoint(client: ProwlarrApiClient, httpx_mock: HTTPXMock):
    """GET /application returns list."""
    httpx_mock.add_response(json=[APPLICATION])
    result = client.get_applications()

    assert len(result) == 1
    assert result[0].id == 1


def test_add_application_posts_config(client: ProwlarrApiClient, httpx_mock: HTTPXMock):
    """POST /application with provided config."""
    httpx_mock.add_response(json=APPLICATION)
    client.add_application({"name": "Radarr"})

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert "/application" in str(request.url)


def test_update_application_includes_id(client: ProwlarrApiClient, httpx_mock: HTTPXMock):
    """PUT /application/{id} injects id into payload."""
    httpx_mock.add_response(json=APPLICATION)
    client.update_application(app_id=1, config={"name": "updated"})

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "PUT"
    assert b'"id": 1' in request.content or b'"id":1' in request.content


def test_delete_application_endpoint(client: ProwlarrApiClient, httpx_mock: HTTPXMock):
    """DELETE /application/{id}."""
    httpx_mock.add_response(status_code=200)
    client.delete_application(app_id=1)

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "DELETE"
    assert "/application/1" in str(request.url)


def test_get_indexers_endpoint(client: ProwlarrApiClient, httpx_mock: HTTPXMock):
    """GET /indexer returns list."""
    httpx_mock.add_response(json=[INDEXER])
    result = client.get_indexers()

    assert len(result) == 1
    assert result[0].name == "NZBgeek"


def test_get_host_config_endpoint(client: ProwlarrApiClient, httpx_mock: HTTPXMock):
    """GET /config/host returns config."""
    httpx_mock.add_response(json=HOST_CONFIG)
    result = client.get_host_config()

    assert result.bind_address == "*"
    assert result.port == 9696


def test_update_host_config_merges_current(client: ProwlarrApiClient, httpx_mock: HTTPXMock):
    """update_host_config fetches current then PUTs merged config."""
    httpx_mock.add_response(json=HOST_CONFIG)
    httpx_mock.add_response(json={**HOST_CONFIG, "urlBase": "/prowlarr"})

    client.update_host_config({"urlBase": "/prowlarr"})

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert requests[0].method == "GET"
    assert requests[1].method == "PUT"
    assert b"bindAddress" in requests[1].content
