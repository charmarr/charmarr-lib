# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Media manager interface for connecting media managers to request managers."""

from typing import Any

from ops import EventBase, EventSource, ObjectEvents
from pydantic import BaseModel, Field

from charmarr_lib.core.enums import MediaManager, RequestManager
from charmarr_lib.core.interfaces._base import (
    EventObservingMixin,
    RelationInterfaceBase,
)


class QualityProfile(BaseModel):
    """Quality profile from Radarr/Sonarr."""

    id: int = Field(description="Quality profile ID from the media manager API")
    name: str = Field(description="Quality profile name (e.g., HD-Bluray+WEB, UHD-Bluray+WEB)")


class MediaManagerProviderData(BaseModel):
    """Data published by media manager charms (Radarr, Sonarr, etc.)."""

    # Connection details
    api_url: str = Field(description="Full API URL (e.g., http://radarr:7878)")
    api_key_secret_id: str = Field(description="Juju secret ID containing API key")

    # Identity
    manager: MediaManager = Field(description="Type of media manager")
    instance_name: str = Field(description="Juju app name (e.g., radarr-4k)")
    base_path: str | None = Field(default=None, description="URL base path if configured")

    # Configuration (populated from media manager API after Recyclarr sync)
    quality_profiles: list[QualityProfile] = Field(
        description="Available quality profiles from the media manager"
    )
    root_folders: list[str] = Field(description="Available root folder paths")
    is_4k: bool = Field(
        default=False,
        description="Whether this instance handles 4K content (set via charm config)",
    )


class MediaManagerRequirerData(BaseModel):
    """Data published by request manager charms (Overseerr, Jellyseerr)."""

    requester: RequestManager = Field(description="Type of request manager")
    instance_name: str = Field(description="Juju application name")


class MediaManagerChangedEvent(EventBase):
    """Event emitted when media-manager relation state changes."""

    pass


class MediaManagerProvider(
    RelationInterfaceBase[MediaManagerProviderData, MediaManagerRequirerData]
):
    """Provider side of media-manager interface (passive - no events)."""

    def __init__(self, charm: Any, relation_name: str = "media-manager") -> None:
        super().__init__(charm, relation_name)

    def _get_remote_data_model(self) -> type[MediaManagerRequirerData]:
        return MediaManagerRequirerData

    def publish_data(self, data: MediaManagerProviderData) -> None:
        """Publish provider data to all relations."""
        self._publish_to_all_relations(data)

    def get_requirers(self) -> list[MediaManagerRequirerData]:
        """Get data from all connected requirer applications."""
        return self._get_all_remote_app_data()


class MediaManagerRequirerEvents(ObjectEvents):
    """Events emitted by MediaManagerRequirer."""

    changed = EventSource(MediaManagerChangedEvent)


class MediaManagerRequirer(
    EventObservingMixin, RelationInterfaceBase[MediaManagerRequirerData, MediaManagerProviderData]
):
    """Requirer side of media-manager interface."""

    on = MediaManagerRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "media-manager") -> None:
        super().__init__(charm, relation_name)
        self._setup_event_observation()

    def _get_remote_data_model(self) -> type[MediaManagerProviderData]:
        return MediaManagerProviderData

    def publish_data(self, data: MediaManagerRequirerData) -> None:
        """Publish requirer data to the relation."""
        self._publish_to_single_relation(data)

    def get_providers(self) -> list[MediaManagerProviderData]:
        """Get data from all connected provider applications."""
        return self._get_all_provider_data()

    def is_ready(self) -> bool:
        """Check if at least one media manager is connected and ready."""
        return len(self.get_providers()) > 0
