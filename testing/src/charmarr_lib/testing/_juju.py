"""Jubilant integration helpers for Juju testing."""

from typing import TYPE_CHECKING

import jubilant

if TYPE_CHECKING:
    from collections.abc import Sequence


def wait_for_active_idle(
    jujus: "jubilant.Juju | Sequence[jubilant.Juju]",
    timeout: int = 60 * 20,
) -> None:
    """Wait for Juju models to be active and idle without errors.

    Uses jubilant's built-in wait conditions with error checking.

    Args:
        jujus: Single Juju instance or list of instances to wait for.
        timeout: Maximum time to wait in seconds (default: 20 minutes).
    """
    if isinstance(jujus, jubilant.Juju):
        jujus = [jujus]

    for juju in jujus:
        juju.wait(jubilant.all_active, delay=5, successes=3, timeout=timeout)
        juju.wait(jubilant.all_active, delay=5, timeout=60 * 5, error=jubilant.any_error)
        juju.wait(jubilant.all_agents_idle, delay=5, timeout=60 * 5, error=jubilant.any_error)
