# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Kubernetes utilities for resource management and patching.

This package provides utilities for interacting with Kubernetes resources
via lightkube, with a focus on patching StatefulSets managed by Juju.

Key components:
- K8sResourceManager: Generic K8s resource operations with retry logic (from charmarr-lib-krm)
- reconcile_storage_volume: Mount shared PVCs in StatefulSets
- reconcile_hardware_transcoding: Mount hardware devices for GPU transcoding
"""

from charmarr_lib.core._k8s._hardware import (
    is_hardware_device_mounted,
    reconcile_hardware_transcoding,
)
from charmarr_lib.core._k8s._storage import (
    is_storage_mounted,
    reconcile_storage_volume,
)
from charmarr_lib.krm import K8sResourceManager, ReconcileResult

__all__ = [
    "K8sResourceManager",
    "ReconcileResult",
    "is_hardware_device_mounted",
    "is_storage_mounted",
    "reconcile_hardware_transcoding",
    "reconcile_storage_volume",
]
