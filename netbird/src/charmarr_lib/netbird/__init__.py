# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Shared NetBird charm library — relation interfaces, Management API client, utilities."""

from charmarr_lib.netbird._api import (
    NetbirdApiConnectionError,
    NetbirdApiError,
    NetbirdApiResponseError,
    NetbirdManagementClient,
    ServiceUserResponse,
    SetupKeyResponse,
    TokenResponse,
)
from charmarr_lib.netbird.constants import (
    API_AUTH_SCHEME,
    API_BASE_PATH,
    MAX_TOKEN_EXPIRY_DAYS,
    NETWORK_ADMIN_ROLE,
)
from charmarr_lib.netbird.interfaces import (
    NetbirdEnrollmentCredentials,
    NetbirdEnrollmentProvider,
    NetbirdEnrollmentProviderData,
    NetbirdEnrollmentRequirer,
    NetbirdEnrollmentRequirerData,
)

__all__ = [
    "API_AUTH_SCHEME",
    "API_BASE_PATH",
    "MAX_TOKEN_EXPIRY_DAYS",
    "NETWORK_ADMIN_ROLE",
    "NetbirdApiConnectionError",
    "NetbirdApiError",
    "NetbirdApiResponseError",
    "NetbirdEnrollmentCredentials",
    "NetbirdEnrollmentProvider",
    "NetbirdEnrollmentProviderData",
    "NetbirdEnrollmentRequirer",
    "NetbirdEnrollmentRequirerData",
    "NetbirdManagementClient",
    "ServiceUserResponse",
    "SetupKeyResponse",
    "TokenResponse",
]
