# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Shared utilities for VPN K8s modules."""

import hashlib


def compute_config_hash(cm_data: dict[str, str]) -> str:
    """Compute short hash of ConfigMap data for pod restart triggering."""
    content = "".join(f"{k}={v}" for k, v in sorted(cm_data.items()))
    return hashlib.sha256(content.encode()).hexdigest()[:8]
