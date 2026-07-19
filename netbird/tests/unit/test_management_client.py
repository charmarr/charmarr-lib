# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Tests for the NetBird Management REST API client."""

import json

import httpx
import pytest
from pytest_httpx import HTTPXMock

from charmarr_lib.netbird import (
    NetbirdApiConnectionError,
    NetbirdApiResponseError,
    NetbirdManagementClient,
)

BASE_URL = "https://netbird.example.com"


def client() -> NetbirdManagementClient:
    return NetbirdManagementClient(BASE_URL, "owner-pat", max_retries=2)


def test_create_service_user_sends_expected_payload(httpx_mock: HTTPXMock):
    """Service-user creation posts the least-privilege payload and parses the response."""
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/api/users",
        json={"id": "u1", "name": "router-a", "role": "network_admin"},
    )

    with client() as c:
        user = c.create_service_user("router-a")

    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["Authorization"] == "Token owner-pat"
    body = json.loads(request.content)
    assert body == {
        "name": "router-a",
        "role": "network_admin",
        "is_service_user": True,
        "auto_groups": [],
    }
    assert user.id == "u1"
    assert user.role == "network_admin"


def test_create_user_token_returns_plain_token(httpx_mock: HTTPXMock):
    """Token creation surfaces the one-time plaintext token."""
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/api/users/u1/tokens",
        json={"id": "t1", "name": "router-a", "plain_token": "nbp_secret"},
    )

    with client() as c:
        token = c.create_user_token("u1", "router-a", expires_in=365)

    assert token.plain_token == "nbp_secret"


def test_create_setup_key_payload(httpx_mock: HTTPXMock):
    """Setup-key creation posts the reusable-key payload."""
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/api/setup-keys",
        json={"id": "k1", "key": "AAAA-BBBB", "name": "router-a"},
    )

    with client() as c:
        key = c.create_setup_key("router-a")

    request = httpx_mock.get_request()
    assert request is not None
    body = json.loads(request.content)
    assert body["type"] == "reusable"
    assert body["expires_in"] == 0
    assert key.key == "AAAA-BBBB"


def test_response_tolerates_unknown_fields(httpx_mock: HTTPXMock):
    """Forward-compat: unknown response fields are tolerated."""
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/api/users",
        json=[{"id": "u1", "role": "network_admin", "brand_new_field": 1}],
    )

    with client() as c:
        users = c.list_users()

    assert users[0].id == "u1"


def test_http_error_maps_to_response_error(httpx_mock: HTTPXMock):
    """A 403 maps to NetbirdApiResponseError carrying the status code."""
    httpx_mock.add_response(method="POST", url=f"{BASE_URL}/api/setup-keys", status_code=403)

    with client() as c, pytest.raises(NetbirdApiResponseError) as exc:
        c.create_setup_key("router-a")

    assert exc.value.status_code == 403


def test_connect_error_maps_to_connection_error(httpx_mock: HTTPXMock):
    """Connection failures (after retries) map to NetbirdApiConnectionError."""
    httpx_mock.add_exception(httpx.ConnectError("boom"), is_reusable=True)

    with client() as c, pytest.raises(NetbirdApiConnectionError):
        c.list_users()
