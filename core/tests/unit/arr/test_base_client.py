# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

# Testing protected methods directly - this is intentional for unit testing base class behavior
# pyright: reportPrivateUsage=false

"""Unit tests for BaseArrApiClient.

Tests focus on:
- Error handling (connection errors, HTTP errors)
- Retry logic for transient failures
- Pydantic response validation
"""

import httpx
import pytest
from pydantic import BaseModel
from pytest_httpx import HTTPXMock

from charmarr_lib.core import ArrApiConnectionError, ArrApiResponseError
from charmarr_lib.core._arr._base_client import BaseArrApiClient


class SampleResponse(BaseModel):
    """Sample Pydantic model for validation tests."""

    id: int
    name: str


@pytest.fixture
def client():
    """Create a test client with minimal retries for faster tests."""
    return BaseArrApiClient(
        base_url="http://localhost:7878",
        api_key="test-api-key",
        api_version="v3",
        max_retries=3,
    )


def test_http_error_raises_response_error_with_status(
    client: BaseArrApiClient, httpx_mock: HTTPXMock
):
    """Test HTTP error status raises ArrApiResponseError with status code."""
    httpx_mock.add_response(status_code=404, text="Not Found")

    with pytest.raises(ArrApiResponseError) as exc_info:
        client._get("/nonexistent")

    assert exc_info.value.status_code == 404


def test_connection_error_raises_after_retries(client: BaseArrApiClient, httpx_mock: HTTPXMock):
    """Test connection failures raise ArrApiConnectionError after exhausting retries."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

    with pytest.raises(ArrApiConnectionError):
        client._get("/test")


def test_timeout_error_raises_after_retries(client: BaseArrApiClient, httpx_mock: HTTPXMock):
    """Test timeout failures raise ArrApiConnectionError after exhausting retries."""
    httpx_mock.add_exception(httpx.TimeoutException("Timed out"))
    httpx_mock.add_exception(httpx.TimeoutException("Timed out"))
    httpx_mock.add_exception(httpx.TimeoutException("Timed out"))

    with pytest.raises(ArrApiConnectionError):
        client._get("/test")


def test_retry_succeeds_after_transient_failure(client: BaseArrApiClient, httpx_mock: HTTPXMock):
    """Test request succeeds when transient failure resolves before retry limit."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    httpx_mock.add_response(json={"status": "ok"})

    result = client._get("/test")

    assert result == {"status": "ok"}


def test_get_validated_parses_to_model(client: BaseArrApiClient, httpx_mock: HTTPXMock):
    """Test _get_validated parses JSON response into Pydantic model."""
    httpx_mock.add_response(json={"id": 1, "name": "test"})

    result = client._get_validated("/item/1", SampleResponse)

    assert isinstance(result, SampleResponse)
    assert result.id == 1
    assert result.name == "test"


def test_get_validated_list_parses_to_models(client: BaseArrApiClient, httpx_mock: HTTPXMock):
    """Test _get_validated_list parses JSON array into list of Pydantic models."""
    httpx_mock.add_response(json=[{"id": 1, "name": "one"}, {"id": 2, "name": "two"}])

    result = client._get_validated_list("/items", SampleResponse)

    assert len(result) == 2
    assert all(isinstance(item, SampleResponse) for item in result)


def test_post_validated_parses_to_model(client: BaseArrApiClient, httpx_mock: HTTPXMock):
    """Test _post_validated parses JSON response into Pydantic model."""
    httpx_mock.add_response(json={"id": 99, "name": "created"})

    result = client._post_validated("/items", {"name": "new"}, SampleResponse)

    assert isinstance(result, SampleResponse)
    assert result.id == 99


def test_put_validated_parses_to_model(client: BaseArrApiClient, httpx_mock: HTTPXMock):
    """Test _put_validated parses JSON response into Pydantic model."""
    httpx_mock.add_response(json={"id": 1, "name": "updated"})

    result = client._put_validated("/items/1", {"name": "updated"}, SampleResponse)

    assert isinstance(result, SampleResponse)
    assert result.name == "updated"
