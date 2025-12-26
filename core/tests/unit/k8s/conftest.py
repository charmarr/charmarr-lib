# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Shared fixtures for core K8s unit tests."""

from unittest.mock import MagicMock

import pytest
from lightkube.models.apps_v1 import StatefulSet, StatefulSetSpec
from lightkube.models.core_v1 import Container, PodSecurityContext, PodSpec, PodTemplateSpec
from lightkube.models.meta_v1 import LabelSelector, ObjectMeta

from charmarr_lib.core import K8sResourceManager


@pytest.fixture
def mock_client():
    """Create a mock lightkube client."""
    return MagicMock()


@pytest.fixture
def manager(mock_client):
    """Create a K8sResourceManager with a mock client."""
    return K8sResourceManager(client=mock_client)


@pytest.fixture
def make_statefulset():
    """Return a factory function to create StatefulSets for testing."""

    def _make_statefulset(
        name: str = "radarr",
        namespace: str = "media",
        volumes: list | None = None,
        container_mounts: list | None = None,
        security_context: PodSecurityContext | None = None,
    ) -> StatefulSet:
        container = Container(name=name, volumeMounts=container_mounts or [])
        return StatefulSet(
            metadata=ObjectMeta(name=name, namespace=namespace),
            spec=StatefulSetSpec(
                selector=LabelSelector(matchLabels={"app": name}),
                serviceName=name,
                template=PodTemplateSpec(
                    spec=PodSpec(
                        containers=[container],
                        volumes=volumes or [],
                        securityContext=security_context,
                    )
                ),
            ),
        )

    return _make_statefulset
