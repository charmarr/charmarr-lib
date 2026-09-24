# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Recyclarr integration for Trash Guides quality profile sync.

This module provides utilities for running Recyclarr to sync quality profiles
and custom formats from Trash Guides to Radarr, Sonarr, and Lidarr.

See ADR: apps/adr-003-recyclarr-integration.md
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from charmarr_lib.core.enums import MediaManager

if TYPE_CHECKING:
    import ops

import ops.pebble

logger = logging.getLogger(__name__)

_RECYCLARR_TIMEOUT = 120.0
_RECYCLARR_BIN_PATH = "/app/recyclarr/recyclarr"
_RECYCLARR_CONFIG_DIR = "/config/configs"
_PLACEHOLDER_KEYS = ("base_url", "api_key")


class RecyclarrError(Exception):
    """Raised when Recyclarr execution fails."""


def _config_path(template: str) -> str:
    """Path Recyclarr writes a materialised template to."""
    return f"{_RECYCLARR_CONFIG_DIR}/{template}.yml"


def _apply_instance_settings(config: str, base_url: str, api_key: str) -> str:
    """Replace a template's placeholder connection settings with real ones.

    Templates ship prompts such as "Put your Radarr URL here" rather than values,
    so the keys are matched instead of the prompt text, which differs per service
    and has changed between releases.
    """
    values = {"base_url": base_url, "api_key": api_key}
    for key in _PLACEHOLDER_KEYS:
        config = re.sub(
            rf"^(\s*){key}:.*$",
            lambda m, k=key: f"{m.group(1)}{k}: {values[k]}",
            config,
            count=1,
            flags=re.MULTILINE,
        )
    return config


def _run(container: ops.Container, command: list[str]) -> str:
    """Run a Recyclarr command, raising RecyclarrError on failure."""
    process = container.exec(command, timeout=_RECYCLARR_TIMEOUT)
    try:
        stdout, _ = process.wait_output()
    except (ops.pebble.ExecError, ops.pebble.ChangeError) as e:
        logger.error("Recyclarr command %s failed: %s", command, e)
        raise RecyclarrError(f"Recyclarr command failed: {e}") from e
    return stdout


def sync_trash_profiles(
    container: ops.Container,
    manager: MediaManager,
    api_key: str,
    profiles_config: str,
    port: int,
    base_url: str | None = None,
) -> None:
    """Sync Trash Guides profiles for the specified media manager.

    Materialises each requested TRaSH Guide template, points it at this instance,
    and syncs. Runs idempotently: templates no longer requested are discarded so a
    narrowed configuration stops syncing what it dropped.

    Args:
        container: Pebble container running the recyclarr image
        manager: The media manager type (RADARR, SONARR, etc.)
        api_key: API key for the media manager
        profiles_config: Comma-separated list of template names
        port: WebUI port for the media manager
        base_url: Optional URL base path (e.g., "/radarr")

    Raises:
        RecyclarrError: If Recyclarr execution fails
    """
    if manager not in (MediaManager.RADARR, MediaManager.SONARR):
        raise RecyclarrError(f"Unsupported media manager for Recyclarr: {manager}")

    templates = [t.strip() for t in profiles_config.split(",") if t.strip()]
    if not templates:
        return

    _run(container, ["rm", "-rf", _RECYCLARR_CONFIG_DIR])

    create = [_RECYCLARR_BIN_PATH, "config", "create"]
    for template in templates:
        create += ["--template", template]
    _run(container, create)

    instance_url = f"http://localhost:{port}{base_url or ''}"
    for template in templates:
        path = _config_path(template)
        config = container.pull(path).read()
        container.push(path, _apply_instance_settings(config, instance_url, api_key))

    logger.info("Recyclarr sync completed: %s", _run(container, [_RECYCLARR_BIN_PATH, "sync"]))
