# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Media storage interface for shared PVC and PUID/PGID coordination."""

from typing import Any

from ops import EventBase, EventSource, Object, ObjectEvents
from pydantic import BaseModel, Field, ValidationError


class MediaStorageProviderData(BaseModel):
    """Data published by charmarr-storage charm."""

    pvc_name: str = Field(description="Name of the shared PVC to mount")
    mount_path: str = Field(
        default="/data", description="Mount path for the shared storage inside containers"
    )
    puid: int = Field(default=1000, description="User ID for file ownership (LinuxServer PUID)")
    pgid: int = Field(default=1000, description="Group ID for file ownership (LinuxServer PGID)")


class MediaStorageRequirerData(BaseModel):
    """Data published by apps mounting storage."""

    instance_name: str = Field(description="Juju application name")


class MediaStorageChangedEvent(EventBase):
    """Event emitted when media-storage relation state changes."""

    pass


class MediaStorageProvider(Object):
    """Provider side of media-storage interface (passive - no events)."""

    def __init__(self, charm: Any, relation_name: str = "media-storage") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

    def publish_data(self, data: MediaStorageProviderData) -> None:
        """Publish provider data to all relations."""
        if not self._charm.unit.is_leader():
            return

        for relation in self._charm.model.relations.get(self._relation_name, []):
            relation.data[self._charm.app]["config"] = data.model_dump_json()

    def get_connected_apps(self) -> list[str]:
        """Get list of connected application names (for logging/metrics)."""
        apps = []
        for relation in self._charm.model.relations.get(self._relation_name, []):
            try:
                app_data = relation.data[relation.app]
                if app_data and "config" in app_data:
                    data = MediaStorageRequirerData.model_validate_json(app_data["config"])
                    apps.append(data.instance_name)
            except (ValidationError, KeyError):
                continue
        return apps


class MediaStorageRequirerEvents(ObjectEvents):
    """Events emitted by MediaStorageRequirer."""

    changed = EventSource(MediaStorageChangedEvent)


class MediaStorageRequirer(Object):
    """Requirer side of media-storage interface."""

    on = MediaStorageRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "media-storage") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        events = charm.on[relation_name]
        self.framework.observe(events.relation_changed, self._emit_changed)
        self.framework.observe(events.relation_broken, self._emit_changed)

    def _emit_changed(self, event: EventBase) -> None:
        self.on.changed.emit()

    def publish_data(self, data: MediaStorageRequirerData) -> None:
        """Publish requirer data to the relation."""
        if not self._charm.unit.is_leader():
            return

        relation = self._charm.model.get_relation(self._relation_name)
        if relation:
            relation.data[self._charm.app]["config"] = data.model_dump_json()

    def get_provider(self) -> MediaStorageProviderData | None:
        """Get storage provider data if available."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return None

        try:
            provider_app = relation.app
            if provider_app:
                provider_data = relation.data[provider_app]
                if provider_data and "config" in provider_data:
                    return MediaStorageProviderData.model_validate_json(provider_data["config"])
        except (ValidationError, KeyError):
            pass
        return None

    def is_ready(self) -> bool:
        """Check if storage is available."""
        return self.get_provider() is not None
