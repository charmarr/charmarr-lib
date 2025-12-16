<p align="center">
  <img src="assets/charmarr-charmarr-lib.png" width="350" alt="Charmarr Lib">
</p>

<p align="center">
  <a href="https://github.com/charmarr/charmarr-lib/actions/workflows/ci.yml"><img src="https://github.com/charmarr/charmarr-lib/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/charmarr-lib-core/"><img src="https://img.shields.io/pypi/v/charmarr-lib-core?label=core" alt="PyPI - core"></a>
  <a href="https://pypi.org/project/charmarr-lib-krm/"><img src="https://img.shields.io/pypi/v/charmarr-lib-krm?label=krm" alt="PyPI - krm"></a>
  <a href="https://pypi.org/project/charmarr-lib-vpn/"><img src="https://img.shields.io/pypi/v/charmarr-lib-vpn?label=vpn" alt="PyPI - vpn"></a>
  <a href="https://pypi.org/project/charmarr-lib-testing/"><img src="https://img.shields.io/pypi/v/charmarr-lib-testing?label=testing" alt="PyPI - testing"></a>
  <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv"></a>
  <a href="https://github.com/charmarr/charmarr-lib/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-LGPL--3.0-blue" alt="License"></a>
</p>

<h1 align="center">Charmarr Library Monorepo</h1>

Shared libraries for Charmarr charms implementing Juju relations and reconcilers, distributed as four pip-installable packages from a single monorepo.

## Packages

| Package | Description |
|---------|-------------|
| **charmarr-lib-core** | Core interfaces, API clients, reconcilers, and storage utilities |
| **charmarr-lib-krm** | Kubernetes Resource Manager with retry logic |
| **charmarr-lib-vpn** | VPN gateway interface and pod-gateway integration |
| **charmarr-lib-testing** | Integration testing utilities with Terraform and Jubilant |

## Installation

```bash
pip install charmarr-lib-core
pip install charmarr-lib-krm
pip install charmarr-lib-vpn
pip install charmarr-lib-testing
```

## Quick Start

### Interfaces

```python
from charmarr_lib.core.interfaces import (
    MediaIndexerProvider,
    DownloadClientRequirer,
    MediaStorageRequirer,
)
```

### API Clients

```python
from charmarr_lib.core import ArrApiClient, ProwlarrApiClient

with ArrApiClient("http://radarr:7878", api_key) as client:
    client.add_root_folder("/movies")
```

### Reconcilers

```python
from charmarr_lib.core import reconcile_download_clients

reconcile_download_clients(client, desired_clients, "radarr", MediaManager.RADARR, get_secret)
```

### K8s Resource Management

```python
from charmarr_lib.krm import K8sResourceManager

manager = K8sResourceManager()
manager.patch(StatefulSet, "my-app", patch_data, "my-namespace")
```

## Development

```bash
# Create and activate virtual environment
uv venv && source .venv/bin/activate

# Install dependencies
uv sync

# Run all checks
tox

# Run specific checks
tox -e lint,fmt    # Linting and formatting
tox -e static      # Type checking
tox -e unit        # Unit tests
```

## Architecture

```
charmarr-lib/
├── core/           # charmarr-lib-core
│   └── src/charmarr_lib/core/
│       ├── interfaces/  # Juju relation interfaces
│       ├── _arr/        # API clients and reconcilers
│       └── _k8s/        # Storage utilities
├── krm/            # charmarr-lib-krm
│   └── src/charmarr_lib/krm/
│       └── _manager.py  # K8sResourceManager
├── vpn/            # charmarr-lib-vpn
│   └── src/charmarr_lib/vpn/
│       ├── interfaces/  # VPN gateway interface
│       └── _k8s/        # Pod-gateway patching
└── testing/        # charmarr-lib-testing
    └── src/charmarr_lib/testing/
        └── _terraform.py, _juju.py
```

## License

LGPL-3.0-or-later
