# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Juju Secrets utilities for Charmarr charms."""

from __future__ import annotations

import ops

_ROTATION_POLICIES: dict[str, ops.SecretRotate | None] = {
    "disabled": None,
    "daily": ops.SecretRotate.DAILY,
    "monthly": ops.SecretRotate.MONTHLY,
    "yearly": ops.SecretRotate.YEARLY,
}


def get_secret_rotation_policy(config_value: str) -> ops.SecretRotate | None:
    """Convert config string to SecretRotate enum.

    Args:
        config_value: One of 'disabled', 'daily', 'monthly', 'yearly'

    Returns:
        SecretRotate enum value or None if disabled
    """
    return _ROTATION_POLICIES.get(config_value.lower())
