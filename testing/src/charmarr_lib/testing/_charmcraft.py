# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Charmcraft.yaml parsing utilities for integration tests."""

from pathlib import Path

import yaml


def get_oci_resources(charm_dir: Path) -> dict[str, str]:
    """Read OCI image resources from charmcraft.yaml.

    Args:
        charm_dir: Path to the charm directory containing charmcraft.yaml.

    Returns:
        Dict mapping resource name to upstream-source image URL.
    """
    charmcraft_path = charm_dir / "charmcraft.yaml"
    with charmcraft_path.open() as f:
        charmcraft = yaml.safe_load(f)
    resources = charmcraft.get("resources", {})
    return {
        name: res["upstream-source"]
        for name, res in resources.items()
        if res.get("type") == "oci-image"
    }
