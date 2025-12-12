# charmarr-lib-vpn

VPN gateway charm library for Kubernetes.

## Features

- VPN gateway Juju relation interface
- StatefulSet patching utilities for pod-gateway integration
- NetworkPolicy kill switch implementation
- Reusable beyond Charmarr ecosystem

## Installation

```bash
pip install charmarr-lib-vpn
```

## Usage

```python
from charmarr_lib.vpn.interfaces import (
    VPNGatewayProvider,
    VPNGatewayRequirer,
)
from charmarr_lib.vpn import (
    patch_gateway_statefulset,
    patch_client_statefulset,
    create_killswitch_network_policy,
)
```

## License

LGPL-3.0-or-later
