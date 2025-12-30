# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for Recyclarr integration."""

from unittest.mock import MagicMock

import ops.pebble
import pytest

from charmarr_lib.core import (
    MediaManager,
    RecyclarrError,
    sync_trash_profiles,
)


@pytest.fixture
def mock_container():
    """Create a mock ops.Container."""
    container = MagicMock()
    container.can_connect.return_value = True
    return container


def test_sync_failure_raises(mock_container):
    """Container exec failure raises RecyclarrError."""
    mock_process = MagicMock()
    mock_process.wait_output.side_effect = ops.pebble.ExecError(
        command=["recyclarr"], exit_code=1, stdout=None, stderr="sync failed"
    )
    mock_container.exec.return_value = mock_process

    with pytest.raises(RecyclarrError, match="sync failed"):
        sync_trash_profiles(
            container=mock_container,
            manager=MediaManager.RADARR,
            api_key="key",
            profiles_config="profile",
            port=7878,
        )


def test_sync_trash_profiles_empty_skips(mock_container):
    """Empty or whitespace profiles_config does not run recyclarr."""
    sync_trash_profiles(
        container=mock_container,
        manager=MediaManager.RADARR,
        api_key="key",
        profiles_config="  ,  ",
        port=7878,
    )
    mock_container.push.assert_not_called()
    mock_container.exec.assert_not_called()


def test_sync_trash_profiles_parses_and_trims(mock_container):
    """Profiles are parsed and expanded to recyclarr include names."""
    mock_process = MagicMock()
    mock_process.wait_output.return_value = ("success", "")
    mock_container.exec.return_value = mock_process

    sync_trash_profiles(
        container=mock_container,
        manager=MediaManager.RADARR,
        api_key="key",
        profiles_config="  hd-bluray-web , uhd-bluray-web  ",
        port=7878,
    )

    push_calls = mock_container.push.call_args_list
    config_call = [c for c in push_calls if "/tmp/recyclarr.yml" in str(c)]
    assert len(config_call) == 1
    config_content = config_call[0][0][1]
    # Templates expanded to include names
    assert "- template: radarr-quality-definition-movie" in config_content
    assert "- template: radarr-quality-profile-hd-bluray-web" in config_content
    assert "- template: radarr-custom-formats-hd-bluray-web" in config_content
    assert "- template: radarr-quality-profile-uhd-bluray-web" in config_content
    assert "- template: radarr-custom-formats-uhd-bluray-web" in config_content
    # Quality definition should only appear once (deduplicated)
    assert config_content.count("radarr-quality-definition-movie") == 1


def test_sync_pushes_config_and_execs(mock_container):
    """Config is pushed to container and recyclarr is executed."""
    mock_process = MagicMock()
    mock_process.wait_output.return_value = ("success", "")
    mock_container.exec.return_value = mock_process

    sync_trash_profiles(
        container=mock_container,
        manager=MediaManager.RADARR,
        api_key="test-key",
        profiles_config="hd-bluray-web",
        port=7878,
        base_url="/radarr",
    )

    assert mock_container.push.call_count == 1
    mock_container.exec.assert_called_once()

    exec_args = mock_container.exec.call_args
    assert "/app/recyclarr/recyclarr" in exec_args[0][0]
    assert "sync" in exec_args[0][0]
