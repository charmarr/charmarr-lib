# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Generic Kubernetes resource operations via lightkube."""

from typing import Any

from lightkube import ApiError, Client
from lightkube.types import CascadeType, PatchType
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


def _is_retriable_error(exc: BaseException) -> bool:
    """Check if an error is retriable.

    Retriable errors:
    - 409 Conflict: Resource was modified between get and patch
    - 429 Too Many Requests: Rate limiting
    - 500 Internal Server Error: Transient server issues
    - 502/503/504: Gateway errors, service unavailable
    - Connection errors: Network issues
    """
    if isinstance(exc, ApiError):
        return exc.status.code in (409, 429, 500, 502, 503, 504)
    return isinstance(exc, OSError)


_retry_on_transient = retry(
    retry=retry_if_exception(_is_retriable_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
    reraise=True,
)


class K8sResourceManager:
    """Generic Kubernetes resource operations via lightkube.

    Provides a simplified interface for common K8s operations:
    - get: Fetch a resource by name
    - patch: Modify an existing resource (strategic merge by default)
    - apply: Create or update a resource (server-side apply)
    - delete: Remove a resource
    - exists: Check if a resource exists

    All mutating operations (patch, apply, delete) automatically retry on:
    - 409 Conflict (optimistic locking failure)
    - 429 Too Many Requests (rate limiting)
    - 5xx Server errors (transient failures)
    - Network/connection errors

    Example:
        manager = K8sResourceManager()
        sts = manager.get(StatefulSet, "radarr", "media")
        manager.patch(StatefulSet, "radarr", patch_data, "media")
    """

    def __init__(
        self,
        client: Client | None = None,
        field_manager: str = "charmarr-lib",
    ) -> None:
        """Initialize the resource manager.

        Args:
            client: Lightkube client. If None, creates a new client using
                    in-cluster config or kubeconfig.
            field_manager: Field manager name for server-side apply operations.
        """
        self._client = client if client is not None else Client()
        self._field_manager = field_manager

    @property
    def client(self) -> Client:
        """Access the underlying lightkube client."""
        return self._client

    def get(self, resource_type: type[Any], name: str, namespace: str | None = None) -> Any:
        """Fetch a resource by name.

        Args:
            resource_type: The resource type (e.g., StatefulSet, NetworkPolicy).
            name: Resource name.
            namespace: Namespace (required for namespaced resources).

        Returns:
            The requested resource.

        Raises:
            ApiError: If the resource doesn't exist or other API errors.
        """
        return self._client.get(resource_type, name, namespace=namespace)  # type: ignore[arg-type]

    @_retry_on_transient
    def patch(
        self,
        resource_type: type[Any],
        name: str,
        obj: dict[str, Any] | Any,
        namespace: str | None = None,
        patch_type: PatchType = PatchType.STRATEGIC,
    ) -> Any:
        """Patch an existing resource.

        Automatically retries on conflict (409) and transient errors.

        Args:
            resource_type: The resource type to patch.
            name: Resource name.
            obj: Patch content (dict or resource object).
            namespace: Namespace (required for namespaced resources).
            patch_type: Patch strategy. Defaults to strategic merge patch.

        Returns:
            The patched resource.

        Raises:
            ApiError: If the resource doesn't exist or patch fails after retries.
        """
        return self._client.patch(  # type: ignore[arg-type]
            resource_type,
            name,
            obj,
            namespace=namespace,
            patch_type=patch_type,
        )

    @_retry_on_transient
    def apply(self, resource: Any, force: bool = False) -> Any:
        """Create or update a resource using server-side apply.

        Server-side apply is idempotent - applying the same resource
        multiple times has no effect. Use this for resources you own
        and want to manage declaratively.

        Automatically retries on conflict and transient errors.

        Args:
            resource: The resource to apply.
            force: Force apply even if there are conflicts.

        Returns:
            The applied resource.

        Raises:
            ApiError: If the apply fails after retries.
        """
        return self._client.apply(  # type: ignore[arg-type]
            resource, field_manager=self._field_manager, force=force
        )

    @_retry_on_transient
    def delete(
        self,
        resource_type: type[Any],
        name: str,
        namespace: str | None = None,
        cascade: CascadeType = CascadeType.BACKGROUND,
    ) -> bool:
        """Delete a resource.

        Automatically retries on transient errors.

        Args:
            resource_type: The resource type to delete.
            name: Resource name.
            namespace: Namespace (required for namespaced resources).
            cascade: Cascade deletion type. Defaults to BACKGROUND.

        Returns:
            True if the resource was deleted, False if it didn't exist.

        Raises:
            ApiError: For errors other than 404 (not found), after retries.
        """
        try:
            self._client.delete(
                resource_type,
                name,
                namespace=namespace,
                cascade=cascade,
            )
            return True
        except ApiError as e:
            if e.status.code == 404:
                return False
            raise

    def exists(
        self,
        resource_type: type[Any],
        name: str,
        namespace: str | None = None,
    ) -> bool:
        """Check if a resource exists.

        Args:
            resource_type: The resource type to check.
            name: Resource name.
            namespace: Namespace (required for namespaced resources).

        Returns:
            True if the resource exists, False otherwise.
        """
        try:
            self._client.get(resource_type, name, namespace=namespace)  # type: ignore[arg-type]
            return True
        except ApiError as e:
            if e.status.code == 404:
                return False
            raise
