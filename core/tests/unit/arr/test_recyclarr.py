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

TEMPLATE = """radarr:
  hd-bluray-web:
    base_url: Put your Radarr URL here
    api_key: Put your API key here

    quality_definition:
      type: movie
"""


@pytest.fixture
def mock_container():
    """Create a mock ops.Container that serves materialised templates."""
    container = MagicMock()
    container.can_connect.return_value = True
    process = MagicMock()
    process.wait_output.return_value = ("success", "")
    container.exec.return_value = process
    container.pull.return_value.read.return_value = TEMPLATE
    return container


def _commands(container) -> list[list[str]]:
    return [call[0][0] for call in container.exec.call_args_list]


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


def test_templates_are_materialised_then_synced(mock_container):
    """Each requested template is created, then a single sync runs."""
    sync_trash_profiles(
        container=mock_container,
        manager=MediaManager.RADARR,
        api_key="key",
        profiles_config="  hd-bluray-web , uhd-bluray-web  ",
        port=7878,
    )

    create = next(c for c in _commands(mock_container) if "create" in c)
    assert create[:3] == ["/app/recyclarr/recyclarr", "config", "create"]
    assert create.count("--template") == 2
    assert "hd-bluray-web" in create and "uhd-bluray-web" in create

    assert _commands(mock_container)[-1] == ["/app/recyclarr/recyclarr", "sync"]


def test_stale_templates_are_discarded_before_creating(mock_container):
    """A narrowed configuration stops syncing what it dropped."""
    sync_trash_profiles(
        container=mock_container,
        manager=MediaManager.RADARR,
        api_key="key",
        profiles_config="hd-bluray-web",
        port=7878,
    )

    commands = _commands(mock_container)
    assert commands[0] == ["rm", "-rf", "/config/configs"]
    assert commands.index(["rm", "-rf", "/config/configs"]) < next(
        i for i, c in enumerate(commands) if "create" in c
    )


def test_placeholders_are_replaced_with_instance_settings(mock_container):
    """The materialised template is pointed at this instance."""
    sync_trash_profiles(
        container=mock_container,
        manager=MediaManager.RADARR,
        api_key="test-key",
        profiles_config="hd-bluray-web",
        port=7878,
        base_url="/radarr",
    )

    path, config = mock_container.push.call_args[0]
    assert path == "/config/configs/hd-bluray-web.yml"
    assert "    base_url: http://localhost:7878/radarr" in config
    assert "    api_key: test-key" in config
    assert "Put your" not in config
    assert "quality_definition:" in config


def test_unsupported_manager_raises(mock_container):
    """Recyclarr only knows how to configure Radarr and Sonarr."""
    with pytest.raises(RecyclarrError, match="Unsupported media manager"):
        sync_trash_profiles(
            container=mock_container,
            manager=MediaManager.LIDARR,
            api_key="key",
            profiles_config="web-1080p",
            port=8686,
        )
