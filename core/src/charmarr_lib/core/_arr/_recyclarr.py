# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Recyclarr integration for Trash Guides quality profile sync.

This module provides utilities for running Recyclarr to sync quality profiles
and custom formats from Trash Guides to Radarr, Sonarr, and Lidarr.

See ADR: apps/adr-003-recyclarr-integration.md
"""

import logging
import os
import subprocess
from pathlib import Path

from charmarr_lib.core.enums import MediaManager

logger = logging.getLogger(__name__)

_RECYCLARR_TIMEOUT = 120


class RecyclarrError(Exception):
    """Raised when Recyclarr execution fails."""

    pass


class RecyclarrTimeoutError(RecyclarrError):
    """Raised when Recyclarr execution times out."""

    pass


def _generate_config(
    manager: MediaManager,
    api_key: str,
    profiles: list[str],
    port: int,
    base_url: str | None,
) -> str:
    """Generate Recyclarr YAML config."""
    config_key = manager.value
    url_base = base_url or ""
    profiles_yaml = "\n".join(f"          - {profile}" for profile in profiles)

    return f"""{config_key}:
  {config_key}:
    base_url: http://localhost:{port}{url_base}
    api_key: {api_key}

    quality_profiles:
      - trash_ids:
{profiles_yaml}
"""


def _run_recyclarr(charm_dir: Path, config_content: str) -> None:
    """Run Recyclarr binary with config."""
    recyclarr_bin = charm_dir / "bin" / "recyclarr"
    if not recyclarr_bin.exists():
        raise RecyclarrError(f"Recyclarr binary not found at {recyclarr_bin}")

    config_path = Path("/tmp/recyclarr.yml")
    try:
        config_path.write_text(config_content)
        env = os.environ.copy()
        env["DOTNET_SYSTEM_GLOBALIZATION_INVARIANT"] = "1"
        result = subprocess.run(
            [str(recyclarr_bin), "sync", "--config", str(config_path)],
            capture_output=True,
            text=True,
            timeout=_RECYCLARR_TIMEOUT,
            check=False,
            env=env,
        )

        if result.returncode != 0:
            output = result.stderr or result.stdout
            logger.error("Recyclarr sync failed: %s", output)
            raise RecyclarrError(f"Recyclarr sync failed: {output}")

        logger.info("Recyclarr sync completed successfully")
    except subprocess.TimeoutExpired as e:
        logger.error("Recyclarr sync timed out after %d seconds", _RECYCLARR_TIMEOUT)
        raise RecyclarrTimeoutError(f"Recyclarr sync timed out after {_RECYCLARR_TIMEOUT}s") from e
    finally:
        config_path.unlink(missing_ok=True)


def sync_trash_profiles(
    charm_dir: Path,
    manager: MediaManager,
    api_key: str,
    profiles_config: str,
    port: int,
    base_url: str | None = None,
) -> None:
    """Sync Trash Guides profiles for the specified media manager.

    Generates Recyclarr config and runs the binary to sync quality profiles
    and custom formats from Trash Guides. Runs idempotently on every reconcile.

    Args:
        charm_dir: Path to the charm directory containing bin/recyclarr
        manager: The media manager type (RADARR, SONARR, etc.)
        api_key: API key for the media manager
        profiles_config: Comma-separated list of profile template names
        port: WebUI port for the media manager
        base_url: Optional URL base path (e.g., "/radarr")

    Raises:
        RecyclarrError: If Recyclarr execution fails
        RecyclarrTimeoutError: If Recyclarr execution times out
    """
    profiles = [p.strip() for p in profiles_config.split(",") if p.strip()]
    if not profiles:
        return

    config = _generate_config(
        manager=manager,
        api_key=api_key,
        profiles=profiles,
        port=port,
        base_url=base_url,
    )
    _run_recyclarr(charm_dir, config)
