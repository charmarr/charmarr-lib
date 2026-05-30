# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Crowsnest interface for fleet observability aggregation.

Charmarr charms provide this relation to opt themselves into the
`charmarr-crowsnest-k8s` fleet view. The provider publishes a URL where
crowsnest can poll the charm's topology endpoint; the requirer (crowsnest)
aggregates across all related peers and serves the result to a Grafana
node-graph plugin.

For v1 the provider side carries one field (`topology_url`). The interface
is intentionally scoped broadly (`crowsnest`, not `topology_poll`) so
future cross-cutting needs - action dispatch, config queries, SLI feedback
- can extend the payload without a new relation.
"""

from typing import Any

from ops import EventBase, EventSource, ObjectEvents
from pydantic import BaseModel, Field

from charmarr_lib.core.interfaces._base import (
    EventObservingMixin,
    RelationInterfaceBase,
)


class CrowsnestProviderData(BaseModel):
    """Data published by a charmarr charm to crowsnest."""

    topology_url: str = Field(
        description=(
            "HTTP URL where this charm's topology endpoint serves the "
            "Prometheus exposition file (charmarr_relation_* metrics). "
            "Typically `http://<app>.<model>.svc.cluster.local:9099/metrics`."
        ),
    )


class CrowsnestChangedEvent(EventBase):
    """Event emitted when the crowsnest relation state changes."""


class CrowsnestProvider(RelationInterfaceBase[CrowsnestProviderData, BaseModel]):
    """Provider side of the crowsnest interface (charmarr fleet charms)."""

    def __init__(self, charm: Any, relation_name: str = "crowsnest") -> None:
        super().__init__(charm, relation_name)

    def _get_remote_data_model(self) -> type[BaseModel]:
        return BaseModel

    def publish_data(self, data: CrowsnestProviderData) -> None:
        """Publish provider data to every related crowsnest unit."""
        self._publish_to_all_relations(data)


class CrowsnestRequirerEvents(ObjectEvents):
    """Events emitted by `CrowsnestRequirer`."""

    changed = EventSource(CrowsnestChangedEvent)


class CrowsnestRequirer(
    EventObservingMixin, RelationInterfaceBase[BaseModel, CrowsnestProviderData]
):
    """Requirer side of the crowsnest interface (charmarr-crowsnest-k8s)."""

    on = CrowsnestRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "crowsnest") -> None:
        super().__init__(charm, relation_name)
        self._setup_event_observation()

    def _get_remote_data_model(self) -> type[CrowsnestProviderData]:
        return CrowsnestProviderData

    def get_providers(self) -> list[CrowsnestProviderData]:
        """Get crowsnest data from every related charmarr peer."""
        return self._get_all_provider_data()

    def is_ready(self) -> bool:
        """At least one provider is wired and publishing."""
        return len(self.get_providers()) > 0
