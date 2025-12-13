# charmarr-lib-krm

Kubernetes Resource Manager with retry logic and reconciliation utilities.

## Features

- Generic CRUD operations for any K8s resource type via lightkube
- Automatic retry on transient errors (409 Conflict, 429 Rate Limit, 5xx)
- Strategic merge patch and server-side apply support
- Reconciliation result types for idempotent operations

## Installation

```bash
pip install charmarr-lib-krm
```

## Usage

```python
from charmarr_lib.krm import K8sResourceManager, ReconcileResult
from lightkube.resources.apps_v1 import StatefulSet

# Create manager (uses in-cluster config or kubeconfig)
manager = K8sResourceManager()

# Get a resource
sts = manager.get(StatefulSet, "my-app", "my-namespace")

# Patch with automatic retry on conflict
manager.patch(StatefulSet, "my-app", patch_data, "my-namespace")

# Server-side apply for idempotent create/update
manager.apply(resource)

# Check existence
if manager.exists(StatefulSet, "my-app", "my-namespace"):
    ...

# Delete with 404 handling
deleted = manager.delete(StatefulSet, "my-app", "my-namespace")
```

## License

LGPL-3.0-or-later
