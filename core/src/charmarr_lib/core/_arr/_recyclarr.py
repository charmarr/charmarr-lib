# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Recyclarr integration for Trash Guides quality profile sync.

This module provides utilities for running Recyclarr to sync quality profiles
and custom formats from Trash Guides to Radarr, Sonarr, and Lidarr.

See ADR: apps/adr-003-recyclarr-integration.md
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from charmarr_lib.core.enums import MediaManager

if TYPE_CHECKING:
    import ops

import ops.pebble

logger = logging.getLogger(__name__)

_RECYCLARR_TIMEOUT = 120.0
_RECYCLARR_BIN_PATH = "/app/recyclarr/recyclarr"
_RECYCLARR_CONFIG_PATH = "/tmp/recyclarr.yml"


class RecyclarrError(Exception):
    """Raised when Recyclarr execution fails."""


def _expand_template_to_includes(manager: MediaManager, template: str) -> list[str]:
    """Expand user-friendly template name to actual Recyclarr include names.

    Recyclarr templates (shown in `config list templates`) are NOT directly usable
    in the `include:` directive. Each template maps to multiple includes:
    - quality-definition (shared across profiles)
    - quality-profile-{template}
    - custom-formats-{template}
    """
    prefix = manager.value
    return [
        f"{prefix}-quality-definition-movie",
        f"{prefix}-quality-profile-{template}",
        f"{prefix}-custom-formats-{template}",
    ]


def _generate_config(
    manager: MediaManager,
    api_key: str,
    templates: list[str],
    port: int,
    base_url: str | None,
) -> str:
    """Generate Recyclarr YAML config using TRaSH Guide templates."""
    config_key = manager.value
    url_base = base_url or ""

    # Expand templates to actual include names and deduplicate
    includes: list[str] = []
    seen: set[str] = set()
    for template in templates:
        for include in _expand_template_to_includes(manager, template):
            if include not in seen:
                includes.append(include)
                seen.add(include)

    includes_yaml = "\n".join(f"      - template: {inc}" for inc in includes)

    return f"""{config_key}:
  {config_key}:
    base_url: http://localhost:{port}{url_base}
    api_key: {api_key}

    include:
{includes_yaml}
"""


def _run_recyclarr_in_container(
    container: ops.Container,
    config_content: str,
) -> None:
    """Run Recyclarr in a container with the official recyclarr image."""
    container.push(_RECYCLARR_CONFIG_PATH, config_content, make_dirs=True)

    process = container.exec(
        [_RECYCLARR_BIN_PATH, "sync", "--config", _RECYCLARR_CONFIG_PATH],
        timeout=_RECYCLARR_TIMEOUT,
    )
    try:
        stdout, _ = process.wait_output()
        logger.info("Recyclarr sync completed: %s", stdout)
    except (ops.pebble.ExecError, ops.pebble.ChangeError) as e:
        logger.error("Recyclarr sync failed: %s", e)
        raise RecyclarrError(f"Recyclarr sync failed: {e}") from e


def sync_trash_profiles(
    container: ops.Container,
    manager: MediaManager,
    api_key: str,
    profiles_config: str,
    port: int,
    base_url: str | None = None,
) -> None:
    """Sync Trash Guides profiles for the specified media manager.

    Generates Recyclarr config and runs it in the provided container
    to sync quality profiles from Trash Guides. Runs idempotently.

    Args:
        container: Pebble container running the recyclarr image
        manager: The media manager type (RADARR, SONARR, etc.)
        api_key: API key for the media manager
        profiles_config: Comma-separated list of profile template names
        port: WebUI port for the media manager
        base_url: Optional URL base path (e.g., "/radarr")

    Raises:
        RecyclarrError: If Recyclarr execution fails
    """
    templates = [t.strip() for t in profiles_config.split(",") if t.strip()]
    if not templates:
        return

    config = _generate_config(
        manager=manager,
        api_key=api_key,
        templates=templates,
        port=port,
        base_url=base_url,
    )
    _run_recyclarr_in_container(container, config)
