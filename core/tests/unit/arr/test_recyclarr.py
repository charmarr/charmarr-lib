# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for Recyclarr integration."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from charmarr_lib.core import (
    MediaManager,
    RecyclarrError,
    RecyclarrTimeoutError,
    sync_trash_profiles,
)


def test_sync_missing_binary_raises(charm_dir_without_recyclarr):
    """Missing binary raises RecyclarrError."""
    with pytest.raises(RecyclarrError, match="not found"):
        sync_trash_profiles(
            charm_dir_without_recyclarr, MediaManager.RADARR, "key", "profile", 7878
        )


def test_sync_failure_raises(charm_dir_with_recyclarr):
    """Non-zero exit code raises RecyclarrError."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="sync failed")
        with pytest.raises(RecyclarrError, match="sync failed"):
            sync_trash_profiles(
                charm_dir_with_recyclarr, MediaManager.RADARR, "key", "profile", 7878
            )


def test_sync_timeout_raises(charm_dir_with_recyclarr):
    """Subprocess timeout raises RecyclarrTimeoutError."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="recyclarr", timeout=120)
        with pytest.raises(RecyclarrTimeoutError):
            sync_trash_profiles(
                charm_dir_with_recyclarr, MediaManager.RADARR, "key", "profile", 7878
            )


def test_sync_cleans_up_config(charm_dir_with_recyclarr):
    """Config file is deleted even on failure."""
    config_path = Path("/tmp/recyclarr.yml")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="error")
        with pytest.raises(RecyclarrError):
            sync_trash_profiles(
                charm_dir_with_recyclarr, MediaManager.RADARR, "key", "profile", 7878
            )
    assert not config_path.exists()


def test_sync_trash_profiles_empty_skips(charm_dir_with_recyclarr):
    """Empty or whitespace profiles_config does not run recyclarr."""
    with patch("charmarr_lib.core._arr._recyclarr._run_recyclarr") as mock_run:
        sync_trash_profiles(charm_dir_with_recyclarr, MediaManager.RADARR, "key", "  ,  ", 7878)
    mock_run.assert_not_called()


def test_sync_trash_profiles_parses_and_trims(charm_dir_with_recyclarr):
    """Profiles are parsed from comma-separated string with whitespace trimmed."""
    with patch("charmarr_lib.core._arr._recyclarr._run_recyclarr") as mock_run:
        sync_trash_profiles(
            charm_dir_with_recyclarr, MediaManager.RADARR, "key", "  a , b  ", 7878
        )
    config = mock_run.call_args[0][1]
    assert "- a\n" in config
    assert "- b\n" in config
