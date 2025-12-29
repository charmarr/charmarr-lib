# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""FlareSolverr interface for Cloudflare bypass proxy."""

from typing import Any

from ops import EventBase, EventSource, Object, ObjectEvents
from pydantic import BaseModel, Field, ValidationError


class FlareSolverrProviderData(BaseModel):
    """Data published by flaresolverr-k8s charm."""

    url: str = Field(description="FlareSolverr API URL (e.g., http://host:8191)")


class FlareSolverrChangedEvent(EventBase):
    """Event emitted when flaresolverr relation state changes."""

    pass


class FlareSolverrProvider(Object):
    """Provider side of flaresolverr interface."""

    def __init__(self, charm: Any, relation_name: str = "flaresolverr") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

    def publish_data(self, data: FlareSolverrProviderData) -> None:
        """Publish provider data to all relations."""
        if not self._charm.unit.is_leader():
            return

        for relation in self._charm.model.relations.get(self._relation_name, []):
            relation.data[self._charm.app]["config"] = data.model_dump_json()


class FlareSolverrRequirerEvents(ObjectEvents):
    """Events emitted by FlareSolverrRequirer."""

    changed = EventSource(FlareSolverrChangedEvent)


class FlareSolverrRequirer(Object):
    """Requirer side of flaresolverr interface."""

    on = FlareSolverrRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "flaresolverr") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        events = charm.on[relation_name]
        self.framework.observe(events.relation_changed, self._emit_changed)
        self.framework.observe(events.relation_broken, self._emit_changed)

    def _emit_changed(self, event: EventBase) -> None:
        self.on.changed.emit()

    def get_provider(self) -> FlareSolverrProviderData | None:
        """Get FlareSolverr provider data if available."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return None

        try:
            provider_app = relation.app
            if provider_app:
                provider_data = relation.data[provider_app]
                if provider_data and "config" in provider_data:
                    return FlareSolverrProviderData.model_validate_json(provider_data["config"])
        except (ValidationError, KeyError):
            pass
        return None

    def is_ready(self) -> bool:
        """Check if FlareSolverr is available."""
        return self.get_provider() is not None
