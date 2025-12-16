<p align="center">
  <img src="../assets/charmarr-charmarr-lib.png" width="350" alt="Charmarr Lib">
</p>

<h1 align="center">charmarr-lib-core</h1>

Core charm libraries for Charmarr media automation.

## Features

- Juju relation interfaces for media automation
- API clients for *arr applications (Radarr, Sonarr, Prowlarr, etc.)
- Reconcilers for managing application configuration
- Pydantic models for type-safe data validation
- K8s storage utilities for StatefulSet patching

## Installation

```bash
pip install charmarr-lib-core
```

## Usage

### Interfaces

```python
from charmarr_lib.core.interfaces import (
    # Media Indexer (Prowlarr <-> Radarr/Sonarr/Lidarr)
    MediaIndexerProvider,
    MediaIndexerRequirer,
    MediaIndexerProviderData,
    MediaIndexerRequirerData,
    # Download Client (qBittorrent/SABnzbd <-> Radarr/Sonarr/Lidarr)
    DownloadClientProvider,
    DownloadClientRequirer,
    DownloadClientProviderData,
    DownloadClientRequirerData,
    # Media Storage (shared PVC <-> all apps)
    MediaStorageProvider,
    MediaStorageRequirer,
    MediaStorageProviderData,
    MediaStorageRequirerData,
    # Media Manager (Radarr/Sonarr <-> Overseerr/Jellyseerr)
    MediaManagerProvider,
    MediaManagerRequirer,
    MediaManagerProviderData,
    MediaManagerRequirerData,
    QualityProfile,
)
```

### API Clients

```python
from charmarr_lib.core import (
    # Radarr/Sonarr/Lidarr client (v3 API)
    ArrApiClient,
    # Prowlarr client (v1 API)
    ProwlarrApiClient,
    # Errors
    ArrApiError,
    ArrApiConnectionError,
    ArrApiResponseError,
)

# Connect to Radarr
with ArrApiClient("http://radarr:7878", api_key) as client:
    profiles = client.get_quality_profiles()
    client.add_root_folder("/movies")
```

### Reconcilers

```python
from charmarr_lib.core import (
    reconcile_download_clients,
    reconcile_media_manager_connections,
    reconcile_root_folder,
    reconcile_external_url,
)

# Sync download clients from relations to Radarr
reconcile_download_clients(
    api_client=arr_client,
    desired_clients=download_client_data_from_relations,
    category="radarr",
    media_manager=MediaManager.RADARR,
    get_secret=lambda sid: model.get_secret(id=sid).get_content(),
)
```

### Storage Utilities

```python
from charmarr_lib.core import (
    reconcile_storage_volume,
    is_storage_mounted,
    K8sResourceManager,
    ReconcileResult,
)

manager = K8sResourceManager()
result = reconcile_storage_volume(
    manager=manager,
    statefulset_name="radarr",
    container_name="radarr",  # from charmcraft.yaml
    namespace="media",
    pvc_name="media-storage",
    mount_path="/data",
)
```
