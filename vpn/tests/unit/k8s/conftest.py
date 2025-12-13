# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Shared fixtures for VPN K8s unit tests."""

from unittest.mock import MagicMock

import pytest
from lightkube.models.apps_v1 import StatefulSet, StatefulSetSpec
from lightkube.models.core_v1 import Container, PodSpec, PodTemplateSpec
from lightkube.models.meta_v1 import LabelSelector, ObjectMeta

from charmarr_lib.krm import K8sResourceManager
from charmarr_lib.vpn.interfaces import VPNGatewayProviderData


@pytest.fixture
def mock_client():
    """Create a mock lightkube client."""
    return MagicMock()


@pytest.fixture
def manager(mock_client):
    """Create a K8sResourceManager with a mock client."""
    return K8sResourceManager(client=mock_client)


@pytest.fixture
def provider_data():
    """Create a VPN gateway provider data fixture."""
    return VPNGatewayProviderData(
        gateway_dns_name="gluetun.vpn-gateway.svc.cluster.local",
        cluster_cidrs="10.1.0.0/16,10.152.183.0/24",
        vpn_connected=True,
        instance_name="gluetun",
    )


@pytest.fixture
def make_statefulset():
    """Return a factory function to create StatefulSets for testing."""

    def _make_statefulset(
        name: str = "gluetun",
        namespace: str = "vpn-gateway",
        init_containers: list | None = None,
        containers: list | None = None,
    ) -> StatefulSet:
        return StatefulSet(
            metadata=ObjectMeta(name=name, namespace=namespace),
            spec=StatefulSetSpec(
                selector=LabelSelector(matchLabels={"app": name}),
                serviceName=name,
                template=PodTemplateSpec(
                    spec=PodSpec(
                        containers=containers or [Container(name=name)],
                        initContainers=init_containers,
                    )
                ),
            ),
        )

    return _make_statefulset
