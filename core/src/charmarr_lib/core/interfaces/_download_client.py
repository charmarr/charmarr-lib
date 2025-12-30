# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Download client interface for download client ↔ media manager integration."""

from typing import Any

from ops import EventBase, EventSource, ObjectEvents
from pydantic import BaseModel, ValidationError, model_validator

from charmarr_lib.core.enums import DownloadClient, DownloadClientType, MediaManager
from charmarr_lib.core.interfaces._base import (
    EventObservingMixin,
    RelationInterfaceBase,
)


class DownloadClientProviderData(BaseModel):
    """Data published by download clients.

    Must have EITHER api_key_secret_id (SABnzbd) OR credentials_secret_id
    (qBittorrent, Deluge, Transmission), but not both.
    """

    api_url: str
    api_key_secret_id: str | None = None
    credentials_secret_id: str | None = None
    client: DownloadClient
    client_type: DownloadClientType
    instance_name: str
    base_path: str | None = None

    @model_validator(mode="after")
    def validate_auth_fields(self) -> "DownloadClientProviderData":
        """Validate that exactly one auth method is provided (XOR)."""
        has_api_key = self.api_key_secret_id is not None
        has_credentials = self.credentials_secret_id is not None

        if not has_api_key and not has_credentials:
            raise ValueError("Must provide either api_key_secret_id or credentials_secret_id")

        if has_api_key and has_credentials:
            raise ValueError("Cannot provide both api_key_secret_id and credentials_secret_id")

        return self


class DownloadClientRequirerData(BaseModel):
    """Data published by media managers."""

    manager: MediaManager
    instance_name: str


class DownloadClientChangedEvent(EventBase):
    """Event emitted when download-client relation state changes."""

    pass


class DownloadClientProvider(
    RelationInterfaceBase[DownloadClientProviderData, DownloadClientRequirerData]
):
    """Provider side of download-client interface."""

    def __init__(self, charm: Any, relation_name: str = "download-client") -> None:
        super().__init__(charm, relation_name)

    def _get_remote_data_model(self) -> type[DownloadClientRequirerData]:
        return DownloadClientRequirerData

    def publish_data(self, data: DownloadClientProviderData) -> None:
        """Publish provider data to all relations."""
        self._publish_to_all_relations(data)

    def get_requirers(self) -> list[DownloadClientRequirerData]:
        """Get all connected requirers with valid data."""
        return self._get_all_remote_app_data()


class DownloadClientRequirerEvents(ObjectEvents):
    """Events emitted by DownloadClientRequirer."""

    changed = EventSource(DownloadClientChangedEvent)


class DownloadClientRequirer(
    EventObservingMixin,
    RelationInterfaceBase[DownloadClientRequirerData, DownloadClientProviderData],
):
    """Requirer side of download-client interface."""

    on = DownloadClientRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "download-client") -> None:
        super().__init__(charm, relation_name)
        self._setup_event_observation()

    def _get_remote_data_model(self) -> type[DownloadClientProviderData]:
        return DownloadClientProviderData

    def publish_data(self, data: DownloadClientRequirerData) -> None:
        """Publish requirer data to all relations."""
        self._publish_to_all_relations(data)

    def get_providers(self) -> list[DownloadClientProviderData]:
        """Get all connected download clients with valid data."""
        return self._get_all_provider_data()

    def is_ready(self) -> bool:
        """Check if requirer has published data and has >=1 valid provider."""
        relations = self._charm.model.relations.get(self._relation_name, [])
        if not relations:
            return False

        try:
            first_relation = relations[0]
            published_data = first_relation.data[self._charm.app]
            if not published_data or "config" not in published_data:
                return False
            DownloadClientRequirerData.model_validate_json(published_data["config"])
        except (ValidationError, KeyError):
            return False

        return len(self.get_providers()) > 0
