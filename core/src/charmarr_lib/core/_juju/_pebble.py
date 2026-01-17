# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Pebble utilities for Juju charms.

Provides utilities for:
- User creation for LinuxServer.io images (PUID/PGID handling)
- Config file change detection via content hashing

LinuxServer.io images use s6-overlay which dynamically creates users based on
PUID/PGID environment variables. When bypassing s6 to run applications directly
via Pebble's user-id/group-id options, users must exist in /etc/passwd and
/etc/group beforehand.
"""

import hashlib
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


def get_config_hash(container: "Container", config_path: str) -> str:
    """Get a short hash of a config file for change detection.

    This hash can be included in a Pebble layer's environment variables
    to trigger automatic service restarts when the config file changes. (Thanks Mike Thamm!)
    Pebble's replan() detects layer changes and restarts affected services.

    Example usage in a charm::

        def _build_pebble_layer(self) -> ops.pebble.LayerDict:
            return {
                "services": {
                    "myservice": {
                        "command": "/app/run",
                        "environment": {
                            # Pebble restarts service when this changes
                            "__CONFIG_HASH": get_config_hash(
                                self._container, "/config/app.ini"
                            ),
                        },
                    }
                }
            }

    Args:
        container: The ops.Container to read from.
        config_path: Path to the config file in the container.

    Returns:
        A 16-character hex hash of the file content, or empty string
        if the file doesn't exist.
    """
    if not container.exists(config_path):
        return ""
    content = container.pull(config_path).read()
    return hashlib.sha256(content.encode()).hexdigest()[:16]
