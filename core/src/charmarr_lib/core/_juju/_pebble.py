# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Pebble user creation utilities for LinuxServer.io images.

LinuxServer.io images use s6-overlay which dynamically creates users based on
PUID/PGID environment variables. When bypassing s6 to run applications directly
via Pebble's user-id/group-id options, users must exist in /etc/passwd and
/etc/group beforehand.

This module provides utilities to create the necessary user/group entries
before Pebble starts the workload.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ops import Container


def ensure_pebble_user(
    container: "Container",
    puid: int,
    pgid: int,
    username: str = "app",
    home_dir: str = "/config",
) -> bool:
    """Ensure user and group entries exist for Pebble's user-id/group-id.

    LinuxServer.io images don't have users for arbitrary UIDs. This function
    adds entries to /etc/passwd and /etc/group so Pebble can run the workload
    with the specified user-id and group-id.

    Args:
        container: The ops.Container to modify.
        puid: User ID for the workload process.
        pgid: Group ID for the workload process.
        username: Username for the passwd/group entries.
        home_dir: Home directory for the user.

    Returns:
        True if any changes were made, False if entries already existed.

    Side Effects:
        Modifies /etc/passwd and /etc/group in the container if the specified
        UID/GID entries do not already exist.
    """
    changed = False

    group_file = container.pull("/etc/group").read()
    if f":{pgid}:" not in group_file:
        group_file += f"{username}:x:{pgid}:\n"
        container.push("/etc/group", group_file)
        changed = True

    passwd_file = container.pull("/etc/passwd").read()
    if f":{puid}:" not in passwd_file:
        passwd_file += f"{username}:x:{puid}:{pgid}::{home_dir}:/bin/false\n"
        container.push("/etc/passwd", passwd_file)
        changed = True

    return changed
