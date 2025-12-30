# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""FlareSolverr interface for Cloudflare bypass proxy."""

from typing import Any

from ops import EventBase, EventSource, ObjectEvents
from pydantic import BaseModel, Field

from charmarr_lib.core.interfaces._base import (
    EventObservingMixin,
    RelationInterfaceBase,
)


class FlareSolverrProviderData(BaseModel):
    """Data published by flaresolverr-k8s charm."""

    url: str = Field(description="FlareSolverr API URL (e.g., http://host:8191)")


class FlareSolverrChangedEvent(EventBase):
    """Event emitted when flaresolverr relation state changes."""

    pass


class FlareSolverrProvider(RelationInterfaceBase[FlareSolverrProviderData, BaseModel]):
    """Provider side of flaresolverr interface."""

    def __init__(self, charm: Any, relation_name: str = "flaresolverr") -> None:
        super().__init__(charm, relation_name)

    def _get_remote_data_model(self) -> type[BaseModel]:
        return BaseModel

    def publish_data(self, data: FlareSolverrProviderData) -> None:
        """Publish provider data to all relations."""
        self._publish_to_all_relations(data)


class FlareSolverrRequirerEvents(ObjectEvents):
    """Events emitted by FlareSolverrRequirer."""

    changed = EventSource(FlareSolverrChangedEvent)


class FlareSolverrRequirer(
    EventObservingMixin, RelationInterfaceBase[BaseModel, FlareSolverrProviderData]
):
    """Requirer side of flaresolverr interface."""

    on = FlareSolverrRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "flaresolverr") -> None:
        super().__init__(charm, relation_name)
        self._setup_event_observation()

    def _get_remote_data_model(self) -> type[FlareSolverrProviderData]:
        return FlareSolverrProviderData

    def get_provider(self) -> FlareSolverrProviderData | None:
        """Get FlareSolverr provider data if available."""
        return self._get_single_provider_data()

    def is_ready(self) -> bool:
        """Check if FlareSolverr is available."""
        return self.get_provider() is not None
