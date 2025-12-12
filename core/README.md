# charmarr-lib-core

Core charm libraries for Charmarr media automation.

## Features

- Juju relation interfaces for media automation
- API clients for *arr applications (Radarr, Sonarr, Prowlarr, etc.)
- Reconcilers for managing application configuration
- Pydantic models for type-safe data validation

## Installation

```bash
pip install charmarr-lib-core
```

## Usage

```python
from charmarr_lib.core.interfaces import (
    MediaIndexerProvider,
    MediaIndexerRequirer,
    DownloadClientProvider,
    DownloadClientRequirer,
)
from charmarr_lib.core import (
    ArrApiClient,
    ProwlarrApiClient,
    reconcile_download_clients,
)
```

## License

LGPL-3.0-or-later
