# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for ArrApiClient."""

import pytest
from pytest_httpx import HTTPXMock

from charmarr_lib.core import ArrApiClient

DOWNLOAD_CLIENT = {
    "id": 1,
    "name": "qbittorrent",
    "enable": True,
    "protocol": "torrent",
    "implementation": "QBittorrent",
}
ROOT_FOLDER = {"id": 1, "path": "/data/movies", "accessible": True}
QUALITY_PROFILE = {"id": 1, "name": "HD-1080p"}
HOST_CONFIG = {"id": 1, "bindAddress": "*", "port": 7878, "urlBase": None}


@pytest.fixture
def client():
    return ArrApiClient(
        base_url="http://localhost:7878",
        api_key="test-api-key",
        max_retries=1,
    )


def test_uses_v3_api_path(client: ArrApiClient, httpx_mock: HTTPXMock):
    """ArrApiClient uses /api/v3/ path prefix."""
    httpx_mock.add_response(json=[])
    client.get_download_clients()

    request = httpx_mock.get_request()
    assert request is not None
    assert "/api/v3/" in str(request.url)


def test_get_download_clients_endpoint(client: ArrApiClient, httpx_mock: HTTPXMock):
    """GET /downloadclient returns list."""
    httpx_mock.add_response(json=[DOWNLOAD_CLIENT])
    result = client.get_download_clients()

    assert len(result) == 1
    assert result[0].id == 1


def test_add_download_client_posts_config(client: ArrApiClient, httpx_mock: HTTPXMock):
    """POST /downloadclient with provided config."""
    httpx_mock.add_response(json=DOWNLOAD_CLIENT)
    client.add_download_client({"name": "qbittorrent"})

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert "/downloadclient" in str(request.url)


def test_update_download_client_includes_id(client: ArrApiClient, httpx_mock: HTTPXMock):
    """PUT /downloadclient/{id} injects id into payload."""
    httpx_mock.add_response(json=DOWNLOAD_CLIENT)
    client.update_download_client(client_id=1, config={"name": "updated"})

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "PUT"
    assert b'"id": 1' in request.content or b'"id":1' in request.content


def test_delete_download_client_endpoint(client: ArrApiClient, httpx_mock: HTTPXMock):
    """DELETE /downloadclient/{id}."""
    httpx_mock.add_response(status_code=200)
    client.delete_download_client(client_id=1)

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "DELETE"
    assert "/downloadclient/1" in str(request.url)


def test_get_root_folders_endpoint(client: ArrApiClient, httpx_mock: HTTPXMock):
    """GET /rootfolder returns list."""
    httpx_mock.add_response(json=[ROOT_FOLDER])
    result = client.get_root_folders()

    assert len(result) == 1
    assert result[0].path == "/data/movies"


def test_add_root_folder_wraps_path(client: ArrApiClient, httpx_mock: HTTPXMock):
    """POST /rootfolder wraps path string in payload."""
    httpx_mock.add_response(json=ROOT_FOLDER)
    client.add_root_folder("/data/movies")

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert b'"path"' in request.content


def test_get_quality_profiles_endpoint(client: ArrApiClient, httpx_mock: HTTPXMock):
    """GET /qualityprofile returns list."""
    httpx_mock.add_response(json=[QUALITY_PROFILE])
    result = client.get_quality_profiles()

    assert len(result) == 1
    assert result[0].name == "HD-1080p"


def test_get_host_config_endpoint(client: ArrApiClient, httpx_mock: HTTPXMock):
    """GET /config/host returns config."""
    httpx_mock.add_response(json=HOST_CONFIG)
    result = client.get_host_config()

    assert result.bind_address == "*"
    assert result.port == 7878


def test_update_host_config_merges_current(client: ArrApiClient, httpx_mock: HTTPXMock):
    """update_host_config fetches current then PUTs merged config."""
    httpx_mock.add_response(json=HOST_CONFIG)
    httpx_mock.add_response(json={**HOST_CONFIG, "urlBase": "/radarr"})

    client.update_host_config({"urlBase": "/radarr"})

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert requests[0].method == "GET"
    assert requests[1].method == "PUT"
    assert b"bindAddress" in requests[1].content
