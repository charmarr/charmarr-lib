# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Media indexer interface for indexer manager ↔ media manager integration."""

from typing import Any

from ops import EventBase, EventSource, ObjectEvents
from pydantic import BaseModel, ValidationError

from charmarr_lib.core.enums import MediaIndexer, MediaManager
from charmarr_lib.core.interfaces._base import (
    EventObservingMixin,
    RelationInterfaceBase,
)


class MediaIndexerProviderData(BaseModel):
    """Data published by the indexer manager."""

    api_url: str
    api_key_secret_id: str
    indexer: MediaIndexer
    base_path: str | None = None


class MediaIndexerRequirerData(BaseModel):
    """Data published by the media manager."""

    api_url: str
    api_key_secret_id: str
    manager: MediaManager
    instance_name: str
    base_path: str | None = None


class MediaIndexerChangedEvent(EventBase):
    """Event emitted when media-indexer relation state changes."""

    pass


class MediaIndexerProviderEvents(ObjectEvents):
    """Events emitted by MediaIndexerProvider."""

    changed = EventSource(MediaIndexerChangedEvent)


class MediaIndexerProvider(
    EventObservingMixin, RelationInterfaceBase[MediaIndexerProviderData, MediaIndexerRequirerData]
):
    """Provider side of media-indexer interface."""

    on = MediaIndexerProviderEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "media-indexer") -> None:
        super().__init__(charm, relation_name)
        self._setup_event_observation()

    def _get_remote_data_model(self) -> type[MediaIndexerRequirerData]:
        return MediaIndexerRequirerData

    def publish_data(self, data: MediaIndexerProviderData) -> None:
        """Publish provider data to all relations."""
        self._publish_to_all_relations(data)

    def get_requirers(self) -> list[MediaIndexerRequirerData]:
        """Get all connected requirers with valid data."""
        return self._get_all_remote_app_data()

    def is_ready(self) -> bool:
        """Check if provider has published data and has >=1 valid requirer."""
        relations = self._charm.model.relations.get(self._relation_name, [])
        if not relations:
            return False

        try:
            first_relation = relations[0]
            published_data = first_relation.data[self._charm.app]
            if not published_data or "config" not in published_data:
                return False
            MediaIndexerProviderData.model_validate_json(published_data["config"])
        except (ValidationError, KeyError):
            return False

        return len(self.get_requirers()) > 0


class MediaIndexerRequirerEvents(ObjectEvents):
    """Events emitted by MediaIndexerRequirer."""

    changed = EventSource(MediaIndexerChangedEvent)


class MediaIndexerRequirer(
    EventObservingMixin, RelationInterfaceBase[MediaIndexerRequirerData, MediaIndexerProviderData]
):
    """Requirer side of media-indexer interface."""

    on = MediaIndexerRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "media-indexer") -> None:
        super().__init__(charm, relation_name)
        self._setup_event_observation()

    def _get_remote_data_model(self) -> type[MediaIndexerProviderData]:
        return MediaIndexerProviderData

    def publish_data(self, data: MediaIndexerRequirerData) -> None:
        """Publish requirer data to relation."""
        self._publish_to_single_relation(data)

    def get_provider_data(self) -> MediaIndexerProviderData | None:
        """Get provider data if available."""
        return self._get_single_provider_data()

    def is_ready(self) -> bool:
        """Check if both requirer and provider have published valid data."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return False

        try:
            published_data = relation.data[self._charm.app]
            if not published_data or "config" not in published_data:
                return False
            MediaIndexerRequirerData.model_validate_json(published_data["config"])
        except (ValidationError, KeyError):
            return False

        return self.get_provider_data() is not None
