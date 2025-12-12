# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Media manager interface for connecting media managers to request managers."""

from typing import Any

from ops import EventBase, EventSource, Object, ObjectEvents
from pydantic import BaseModel, Field, ValidationError

from charmarr_lib.core.enums import MediaManager, RequestManager


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


class MediaManagerProvider(Object):
    """Provider side of media-manager interface (passive - no events)."""

    def __init__(self, charm: Any, relation_name: str = "media-manager") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

    def publish_data(self, data: MediaManagerProviderData) -> None:
        """Publish provider data to all relations."""
        if not self._charm.unit.is_leader():
            return

        for relation in self._charm.model.relations.get(self._relation_name, []):
            relation.data[self._charm.app]["config"] = data.model_dump_json()

    def get_requirers(self) -> list[MediaManagerRequirerData]:
        """Get data from all connected requirer applications."""
        requirers = []
        for relation in self._charm.model.relations.get(self._relation_name, []):
            try:
                app_data = relation.data[relation.app]
                if app_data and "config" in app_data:
                    data = MediaManagerRequirerData.model_validate_json(app_data["config"])
                    requirers.append(data)
            except (ValidationError, KeyError):
                continue
        return requirers


class MediaManagerRequirerEvents(ObjectEvents):
    """Events emitted by MediaManagerRequirer."""

    changed = EventSource(MediaManagerChangedEvent)


class MediaManagerRequirer(Object):
    """Requirer side of media-manager interface."""

    on = MediaManagerRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "media-manager") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        events = charm.on[relation_name]
        self.framework.observe(events.relation_changed, self._emit_changed)
        self.framework.observe(events.relation_broken, self._emit_changed)

    def _emit_changed(self, event: EventBase) -> None:
        self.on.changed.emit()

    def publish_data(self, data: MediaManagerRequirerData) -> None:
        """Publish requirer data to the relation."""
        if not self._charm.unit.is_leader():
            return

        relation = self._charm.model.get_relation(self._relation_name)
        if relation:
            relation.data[self._charm.app]["config"] = data.model_dump_json()

    def get_providers(self) -> list[MediaManagerProviderData]:
        """Get data from all connected provider applications."""
        providers = []
        for relation in self._charm.model.relations.get(self._relation_name, []):
            try:
                provider_app = relation.app
                if provider_app:
                    provider_data = relation.data[provider_app]
                    if provider_data and "config" in provider_data:
                        data = MediaManagerProviderData.model_validate_json(
                            provider_data["config"]
                        )
                        providers.append(data)
            except (ValidationError, KeyError):
                continue
        return providers

    def is_ready(self) -> bool:
        """Check if at least one media manager is connected and ready."""
        return len(self.get_providers()) > 0
