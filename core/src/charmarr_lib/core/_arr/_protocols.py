# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Protocols for *arr API clients.

These protocols define the contracts that API clients must follow
to be used with the generic reconcilers. Implementations typically
extend BaseArrApiClient for HTTP mechanics.
"""

from typing import Any, Protocol

from pydantic import BaseModel


class MediaManagerConnection(BaseModel):
    """A media manager connection registered in an indexer.

    Represents a connection from an indexer (e.g., Prowlarr) to a
    media manager (e.g., Radarr, Sonarr). The indexer syncs indexers
    to these connected applications.
    """

    id: int
    name: str


class MediaIndexerClient(Protocol):
    """Protocol for media indexer API clients (e.g., Prowlarr).

    Any client implementing this protocol can be used with
    reconcile_media_manager_connections. Implementations typically
    extend BaseArrApiClient and add these methods.
    """

    def get_applications(self) -> list[MediaManagerConnection]:
        """Get all configured media manager connections."""
        ...

    def get_application(self, app_id: int) -> dict[str, Any]:
        """Get a single application by ID as raw dict."""
        ...

    def add_application(self, config: dict[str, Any]) -> Any:
        """Add a new media manager connection."""
        ...

    def update_application(self, app_id: int, config: dict[str, Any]) -> Any:
        """Update an existing media manager connection."""
        ...

    def delete_application(self, app_id: int) -> None:
        """Delete a media manager connection."""
        ...
