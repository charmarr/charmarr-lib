# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for ingress discovery helpers."""

from types import SimpleNamespace
from typing import Any, cast
from unittest import mock

import pytest

from charmarr_lib.testing import get_ingress_ip, get_ingress_url


def _juju_with_status(apps: dict[str, str]) -> Any:
    """Build a stub Juju whose status reports the given app status messages."""
    status = SimpleNamespace(
        apps={
            name: SimpleNamespace(app_status=SimpleNamespace(message=message))
            for name, message in apps.items()
        }
    )
    return SimpleNamespace(status=lambda: status)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Serving at 10.0.0.1", "10.0.0.1"),
        ("Serving at http://192.168.0.133", "192.168.0.133"),
        ("Serving at https://192.168.0.133", "192.168.0.133"),
    ],
)
def test_get_ingress_ip_parses_both_provider_formats(message: str, expected: str) -> None:
    """istio-ingress reports a bare IP, traefik prefixes it with a scheme."""
    juju = _juju_with_status({"ingress": message})
    assert get_ingress_ip(juju, "ingress") == expected


def test_get_ingress_ip_returns_none_for_unparseable_message() -> None:
    """A status message without an address yields None."""
    juju = _juju_with_status({"ingress": "Waiting for gateway address"})
    assert get_ingress_ip(juju, "ingress") is None


def test_get_ingress_ip_returns_none_when_app_absent() -> None:
    """An ingress app missing from the model yields None."""
    juju = _juju_with_status({})
    assert get_ingress_ip(juju, "ingress") is None


def test_get_ingress_url_strips_trailing_slash() -> None:
    """The published URL is normalised so callers can append a path."""
    with mock.patch(
        "charmarr_lib.testing._ingress.get_app_relation_data",
        return_value={"url": "http://192.168.0.133/model-radarr/"},
    ):
        assert get_ingress_url(cast(Any, None), "radarr") == "http://192.168.0.133/model-radarr"


def test_get_ingress_url_returns_none_when_nothing_published() -> None:
    """An unrelated or not-yet-settled ingress relation yields None."""
    with mock.patch(
        "charmarr_lib.testing._ingress.get_app_relation_data",
        return_value={},
    ):
        assert get_ingress_url(cast(Any, None), "radarr") is None
