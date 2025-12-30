# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for testing utilities."""

import os
from unittest import mock

from charmarr_lib.testing import vpn_creds_available


def test_vpn_creds_available_returns_true_when_env_var_set() -> None:
    """Returns True when WIREGUARD_PRIVATE_KEY is set."""
    with mock.patch.dict(os.environ, {"WIREGUARD_PRIVATE_KEY": "test-key"}):
        assert vpn_creds_available() is True


def test_vpn_creds_available_returns_false_when_env_var_not_set() -> None:
    """Returns False when WIREGUARD_PRIVATE_KEY is not set."""
    env = os.environ.copy()
    env.pop("WIREGUARD_PRIVATE_KEY", None)
    with mock.patch.dict(os.environ, env, clear=True):
        assert vpn_creds_available() is False


def test_vpn_creds_available_returns_false_when_env_var_empty() -> None:
    """Returns False when WIREGUARD_PRIVATE_KEY is empty string."""
    with mock.patch.dict(os.environ, {"WIREGUARD_PRIVATE_KEY": ""}):
        assert vpn_creds_available() is False
