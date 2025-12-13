# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for K8sResourceManager."""

from charmarr_lib.krm import K8sResourceManager, ReconcileResult


def test_reconcile_result_immutable() -> None:
    """ReconcileResult should be immutable (frozen dataclass)."""
    result = ReconcileResult(changed=True, message="test")
    assert result.changed is True
    assert result.message == "test"


def test_k8s_resource_manager_import() -> None:
    """K8sResourceManager should be importable."""
    assert K8sResourceManager is not None
