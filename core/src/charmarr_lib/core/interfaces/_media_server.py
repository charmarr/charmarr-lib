# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Media server interface for connecting media servers (Plex, Jellyfin) to request managers."""

from typing import Any

from ops import EventBase, EventSource, ObjectEvents
from pydantic import BaseModel, Field

from charmarr_lib.core.interfaces._base import (
    EventObservingMixin,
    RelationInterfaceBase,
)


class MediaServerProviderData(BaseModel):
    """Data published by media server charms (Plex, Jellyfin)."""

    name: str = Field(description="Server name (e.g., 'My Plex Server')")
    api_url: str = Field(description="API URL (e.g., http://plex-k8s:32400)")
    web_url: str | None = Field(
        default=None,
        description="Optional web UI URL for 'Open in Plex' links",
    )


class MediaServerChangedEvent(EventBase):
    """Event emitted when media-server relation state changes."""

    pass


class MediaServerProvider(RelationInterfaceBase[MediaServerProviderData, BaseModel]):
    """Provider side of media-server interface (Plex, Jellyfin)."""

    def __init__(self, charm: Any, relation_name: str = "media-server") -> None:
        super().__init__(charm, relation_name)

    def _get_remote_data_model(self) -> type[BaseModel]:
        return BaseModel

    def publish_data(self, data: MediaServerProviderData) -> None:
        """Publish provider data to all relations."""
        self._publish_to_all_relations(data)


class MediaServerRequirerEvents(ObjectEvents):
    """Events emitted by MediaServerRequirer."""

    changed = EventSource(MediaServerChangedEvent)


class MediaServerRequirer(
    EventObservingMixin, RelationInterfaceBase[BaseModel, MediaServerProviderData]
):
    """Requirer side of media-server interface (Overseerr, Jellyseerr)."""

    on = MediaServerRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "media-server") -> None:
        super().__init__(charm, relation_name)
        self._setup_event_observation()

    def _get_remote_data_model(self) -> type[MediaServerProviderData]:
        return MediaServerProviderData

    def get_provider(self) -> MediaServerProviderData | None:
        """Get media server provider data if available."""
        return self._get_single_provider_data()

    def is_ready(self) -> bool:
        """Check if a media server is available."""
        return self.get_provider() is not None
