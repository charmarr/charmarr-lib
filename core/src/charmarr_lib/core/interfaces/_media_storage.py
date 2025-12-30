# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Media storage interface for shared PVC and PUID/PGID coordination."""

from typing import Any

from ops import EventBase, EventSource, ObjectEvents
from pydantic import BaseModel, Field

from charmarr_lib.core.interfaces._base import (
    EventObservingMixin,
    RelationInterfaceBase,
)


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


class MediaStorageProvider(
    RelationInterfaceBase[MediaStorageProviderData, MediaStorageRequirerData]
):
    """Provider side of media-storage interface (passive - no events)."""

    def __init__(self, charm: Any, relation_name: str = "media-storage") -> None:
        super().__init__(charm, relation_name)

    def _get_remote_data_model(self) -> type[MediaStorageRequirerData]:
        return MediaStorageRequirerData

    def publish_data(self, data: MediaStorageProviderData) -> None:
        """Publish provider data to all relations."""
        self._publish_to_all_relations(data)

    def get_connected_apps(self) -> list[str]:
        """Get list of connected application names (for logging/metrics)."""
        return [r.instance_name for r in self._get_all_remote_app_data()]


class MediaStorageRequirerEvents(ObjectEvents):
    """Events emitted by MediaStorageRequirer."""

    changed = EventSource(MediaStorageChangedEvent)


class MediaStorageRequirer(
    EventObservingMixin, RelationInterfaceBase[MediaStorageRequirerData, MediaStorageProviderData]
):
    """Requirer side of media-storage interface."""

    on = MediaStorageRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "media-storage") -> None:
        super().__init__(charm, relation_name)
        self._setup_event_observation()

    def _get_remote_data_model(self) -> type[MediaStorageProviderData]:
        return MediaStorageProviderData

    def publish_data(self, data: MediaStorageRequirerData) -> None:
        """Publish requirer data to the relation."""
        self._publish_to_single_relation(data)

    def get_provider(self) -> MediaStorageProviderData | None:
        """Get storage provider data if available."""
        return self._get_single_provider_data()

    def is_ready(self) -> bool:
        """Check if storage is available."""
        return self.get_provider() is not None
