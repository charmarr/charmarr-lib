# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Base classes for Juju relation interfaces."""

from abc import abstractmethod
from typing import Any

from ops import EventBase, Object
from pydantic import BaseModel, ValidationError


class RelationInterfaceBase[TData: BaseModel, TRemote: BaseModel](Object):
    """Base class for relation interfaces with common patterns."""

    def __init__(self, charm: Any, relation_name: str) -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

    def _publish_to_all_relations(self, data: TData) -> None:
        """Publish data to all relations on this endpoint."""
        if not self._charm.unit.is_leader():
            return

        for relation in self._charm.model.relations.get(self._relation_name, []):
            relation.data[self._charm.app]["config"] = data.model_dump_json()

    def _publish_to_single_relation(self, data: TData) -> None:
        """Publish data to the single relation on this endpoint."""
        if not self._charm.unit.is_leader():
            return

        relation = self._charm.model.get_relation(self._relation_name)
        if relation:
            relation.data[self._charm.app]["config"] = data.model_dump_json()

    @abstractmethod
    def _get_remote_data_model(self) -> type[TRemote]:
        """Return the Pydantic model class for parsing remote data."""
        ...

    def _get_all_remote_app_data(self) -> list[TRemote]:
        """Get parsed data from all remote applications on this endpoint."""
        model_cls = self._get_remote_data_model()
        results: list[TRemote] = []
        for relation in self._charm.model.relations.get(self._relation_name, []):
            try:
                app_data = relation.data[relation.app]
                if app_data and "config" in app_data:
                    results.append(model_cls.model_validate_json(app_data["config"]))
            except (ValidationError, KeyError):
                continue
        return results

    def _get_all_provider_data(self) -> list[TRemote]:
        """Get parsed data from all provider applications (for requirers with multiple relations)."""
        model_cls = self._get_remote_data_model()
        results: list[TRemote] = []
        for relation in self._charm.model.relations.get(self._relation_name, []):
            try:
                provider_app = relation.app
                if provider_app:
                    app_data = relation.data[provider_app]
                    if app_data and "config" in app_data:
                        results.append(model_cls.model_validate_json(app_data["config"]))
            except (ValidationError, KeyError):
                continue
        return results

    def _get_single_provider_data(self) -> TRemote | None:
        """Get parsed data from a single provider (for single-relation requirers)."""
        model_cls = self._get_remote_data_model()
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return None

        try:
            provider_app = relation.app
            if provider_app:
                app_data = relation.data[provider_app]
                if app_data and "config" in app_data:
                    return model_cls.model_validate_json(app_data["config"])
        except (ValidationError, KeyError):
            pass
        return None


class EventObservingMixin:
    """Mixin for interfaces that observe relation events and emit custom events."""

    _charm: Any
    _relation_name: str

    def _setup_event_observation(self) -> None:
        """Set up observation of relation_changed and relation_broken events."""
        events = self._charm.on[self._relation_name]
        self.framework.observe(events.relation_changed, self._emit_changed)  # type: ignore[attr-defined]
        self.framework.observe(events.relation_broken, self._emit_changed)  # type: ignore[attr-defined]

    def _emit_changed(self, event: EventBase) -> None:
        """Emit the custom 'changed' event."""
        self.on.changed.emit()  # type: ignore[attr-defined]
