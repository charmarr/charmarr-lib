# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Media indexer interface for indexer manager ↔ media manager integration."""

from typing import Any

from ops import EventBase, EventSource, Object, ObjectEvents
from pydantic import BaseModel, ValidationError

from charmarr_lib.core.enums import MediaIndexer, MediaManager


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


class MediaIndexerProvider(Object):
    """Provider side of media-indexer interface."""

    on = MediaIndexerProviderEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "media-indexer") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        events = charm.on[relation_name]
        self.framework.observe(events.relation_changed, self._emit_changed)
        self.framework.observe(events.relation_broken, self._emit_changed)

    def _emit_changed(self, event: EventBase) -> None:
        self.on.changed.emit()

    def publish_data(self, data: MediaIndexerProviderData) -> None:
        """Publish provider data to all relations."""
        for relation in self._charm.model.relations.get(self._relation_name, []):
            relation.data[self._charm.app]["config"] = data.model_dump_json()

    def get_requirers(self) -> list[MediaIndexerRequirerData]:
        """Get all connected requirers with valid data."""
        requirers = []
        for relation in self._charm.model.relations.get(self._relation_name, []):
            for _unit in relation.units:
                try:
                    app_data = relation.data[relation.app]
                    if app_data and "config" in app_data:
                        requirers.append(
                            MediaIndexerRequirerData.model_validate_json(app_data["config"])
                        )
                except (ValidationError, KeyError):
                    continue
        return requirers

    def is_ready(self) -> bool:
        """Check if provider has published data and has ≥1 valid requirer."""
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


class MediaIndexerRequirer(Object):
    """Requirer side of media-indexer interface."""

    on = MediaIndexerRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "media-indexer") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        events = charm.on[relation_name]
        self.framework.observe(events.relation_changed, self._emit_changed)
        self.framework.observe(events.relation_broken, self._emit_changed)

    def _emit_changed(self, event: EventBase) -> None:
        self.on.changed.emit()

    def publish_data(self, data: MediaIndexerRequirerData) -> None:
        """Publish requirer data to relation."""
        relation = self._charm.model.get_relation(self._relation_name)
        if relation:
            relation.data[self._charm.app]["config"] = data.model_dump_json()

    def get_provider_data(self) -> MediaIndexerProviderData | None:
        """Get provider data if available."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return None

        try:
            provider_app = relation.app
            if provider_app:
                app_data = relation.data[provider_app]
                if app_data and "config" in app_data:
                    return MediaIndexerProviderData.model_validate_json(app_data["config"])
        except (ValidationError, KeyError):
            pass

        return None

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
