# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Kubernetes Resource Manager with retry logic and reconciliation utilities.

This package provides utilities for interacting with Kubernetes resources
via lightkube, with automatic retry on transient errors.

Key components:
- K8sResourceManager: Generic K8s resource operations (get/patch/apply/delete)
- ReconcileResult: Return type for idempotent reconciliation operations
"""

from charmarr_lib.krm._manager import K8sResourceManager
from charmarr_lib.krm._models import ReconcileResult

__all__ = [
    "K8sResourceManager",
    "ReconcileResult",
]
