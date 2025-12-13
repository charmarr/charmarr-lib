# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Data models for K8s reconciliation operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReconcileResult:
    """Result of a reconcile operation.

    Attributes:
        changed: Whether the reconciliation made any changes.
        message: Human-readable description of what happened.
    """

    changed: bool
    message: str
