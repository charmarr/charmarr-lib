# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""API clients, config builders, and reconcilers for *arr applications."""

from charmarr_lib.core._arr._arr_client import (
    ArrApiClient,
    DownloadClientResponse,
    HostConfigResponse,
    QualityProfileResponse,
    RootFolderResponse,
)
from charmarr_lib.core._arr._base_client import (
    ArrApiConnectionError,
    ArrApiError,
    ArrApiResponseError,
)
from charmarr_lib.core._arr._config_builders import (
    ApplicationConfigBuilder,
    DownloadClientConfigBuilder,
    SecretGetter,
)
from charmarr_lib.core._arr._prowlarr_client import (
    ApplicationResponse,
    IndexerResponse,
    ProwlarrApiClient,
    ProwlarrHostConfigResponse,
)

__all__ = [
    "ApplicationConfigBuilder",
    "ApplicationResponse",
    "ArrApiClient",
    "ArrApiConnectionError",
    "ArrApiError",
    "ArrApiResponseError",
    "DownloadClientConfigBuilder",
    "DownloadClientResponse",
    "HostConfigResponse",
    "IndexerResponse",
    "ProwlarrApiClient",
    "ProwlarrHostConfigResponse",
    "QualityProfileResponse",
    "RootFolderResponse",
    "SecretGetter",
]
