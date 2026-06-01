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
    app_name: str = Field(
        default="",
        description=(
            "The local Juju application name of the publishing charm. Lets "
            "crowsnest distinguish same-named apps that live in different "
            "models (e.g. a local `plex` and a cross-model `plex`)."
        ),
    )
    model_name: str = Field(
        default="",
        description=(
            "The local Juju model name of the publishing charm. Used by "
            "crowsnest to compose stable per-app node IDs and to surface "
            "the source model in hover details when fleet members span "
            "multiple models via cross-model relations."
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
        """Publish provider data to every related crowsnest unit.

        `app_name` and `model_name` are auto-populated from the charm if the
        caller left them blank, so providers only need to supply `topology_url`.
        """
        if not data.app_name:
            data = data.model_copy(update={"app_name": self._charm.app.name})
        if not data.model_name:
            data = data.model_copy(update={"model_name": self._charm.model.name})
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
