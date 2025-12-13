# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Kubernetes utilities for resource management and patching.

This package provides utilities for interacting with Kubernetes resources
via lightkube, with a focus on patching StatefulSets managed by Juju.

Key components:
- K8sResourceManager: Generic K8s resource operations with retry logic
- reconcile_storage_volume: Mount shared PVCs in StatefulSets
"""

from charmarr_lib.core._k8s._manager import K8sResourceManager
from charmarr_lib.core._k8s._storage import (
    ReconcileResult,
    is_storage_mounted,
    reconcile_storage_volume,
)

__all__ = [
    "K8sResourceManager",
    "ReconcileResult",
    "is_storage_mounted",
    "reconcile_storage_volume",
]
