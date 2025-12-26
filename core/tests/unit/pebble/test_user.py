# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for Pebble user creation utilities."""

from io import StringIO
from unittest.mock import MagicMock

from charmarr_lib.core import ensure_pebble_user


def test_creates_entries_when_missing():
    """Creates user and group entries when missing."""
    container = MagicMock()
    container.pull.side_effect = [
        StringIO("root:x:0:\n"),
        StringIO("root:x:0:0::/root:/bin/sh\n"),
    ]

    assert ensure_pebble_user(container, puid=1000, pgid=1000) is True
    assert container.push.call_count == 2


def test_no_changes_when_both_exist():
    """Returns False when both user and group already exist."""
    container = MagicMock()
    container.pull.side_effect = [
        StringIO("root:x:0:\napp:x:1000:\n"),
        StringIO("root:x:0:0::/root:/bin/sh\napp:x:1000:1000::/config:/bin/false\n"),
    ]

    assert ensure_pebble_user(container, puid=1000, pgid=1000) is False
    assert container.push.call_count == 0
