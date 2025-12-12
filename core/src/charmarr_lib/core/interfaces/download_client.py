# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Download client interface for download client ↔ media manager integration."""

from typing import Any

from ops import EventBase, EventSource, Object, ObjectEvents
from pydantic import BaseModel, ValidationError, model_validator

from charmarr_lib.core.enums import DownloadClient, DownloadClientType, MediaManager


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


class DownloadClientProvider(Object):
    """Provider side of download-client interface."""

    def __init__(self, charm: Any, relation_name: str = "download-client") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

    def publish_data(self, data: DownloadClientProviderData) -> None:
        """Publish provider data to all relations."""
        for relation in self._charm.model.relations.get(self._relation_name, []):
            relation.data[self._charm.app]["config"] = data.model_dump_json()

    def get_requirers(self) -> list[DownloadClientRequirerData]:
        """Get all connected requirers with valid data."""
        requirers = []
        for relation in self._charm.model.relations.get(self._relation_name, []):
            for _unit in relation.units:
                try:
                    app_data = relation.data[relation.app]
                    if app_data and "config" in app_data:
                        requirers.append(
                            DownloadClientRequirerData.model_validate_json(app_data["config"])
                        )
                except (ValidationError, KeyError):
                    continue
        return requirers


class DownloadClientRequirerEvents(ObjectEvents):
    """Events emitted by DownloadClientRequirer."""

    changed = EventSource(DownloadClientChangedEvent)


class DownloadClientRequirer(Object):
    """Requirer side of download-client interface."""

    on = DownloadClientRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "download-client") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        events = charm.on[relation_name]
        self.framework.observe(events.relation_changed, self._emit_changed)
        self.framework.observe(events.relation_broken, self._emit_changed)

    def _emit_changed(self, event: EventBase) -> None:
        self.on.changed.emit()

    def publish_data(self, data: DownloadClientRequirerData) -> None:
        """Publish requirer data to all relations."""
        for relation in self._charm.model.relations.get(self._relation_name, []):
            relation.data[self._charm.app]["config"] = data.model_dump_json()

    def get_providers(self) -> list[DownloadClientProviderData]:
        """Get all connected download clients with valid data."""
        providers = []
        for relation in self._charm.model.relations.get(self._relation_name, []):
            try:
                provider_app = relation.app
                if provider_app:
                    app_data = relation.data[provider_app]
                    if app_data and "config" in app_data:
                        providers.append(
                            DownloadClientProviderData.model_validate_json(app_data["config"])
                        )
            except (ValidationError, KeyError):
                continue
        return providers

    def is_ready(self) -> bool:
        """Check if requirer has published data and has ≥1 valid provider."""
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
