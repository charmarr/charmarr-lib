<p align="center">
  <img src="../assets/charmarr-charmarr-lib.png" width="350" alt="Charmarr Lib">
</p>

<h1 align="center">charmarr-lib-vpn</h1>

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

### Interfaces

```python
from charmarr_lib.vpn.interfaces import (
    VPNGatewayProvider,
    VPNGatewayRequirer,
    VPNGatewayProviderData,
    VPNGatewayRequirerData,
    VPNGatewayChangedEvent,
)
```

### Gateway Patching (VPN gateway side - gluetun)

```python
from charmarr_lib.vpn import (
    reconcile_gateway,
    build_gateway_patch,
    is_gateway_patched,
)
from charmarr_lib.krm import K8sResourceManager

manager = K8sResourceManager()
provider_data = VPNGatewayProviderData(
    vxlan_id=42,
    vxlan_ip_network="172.16.0.0/24",
    cluster_cidrs="10.1.0.0/16,10.152.183.0/24",
)

# Idempotent reconciliation
result = reconcile_gateway(
    manager=manager,
    statefulset_name="gluetun",
    namespace="vpn-gateway",
    data=provider_data,
    pod_cidr="10.1.0.0/16",
)
```

### Client Patching (Download client side - qBittorrent)

```python
from charmarr_lib.vpn import (
    reconcile_gateway_client,
    build_gateway_client_patch,
    build_gateway_client_configmap_data,
    is_gateway_client_patched,
)

# Create client-side VPN routing
result = reconcile_gateway_client(
    manager=manager,
    statefulset_name="qbittorrent",
    namespace="download-clients",
    data=requirer_data,
    configmap_name="qbittorrent-vpn-config",
)
```

### Kill Switch (NetworkPolicy)

```python
from charmarr_lib.vpn import (
    KillSwitchConfig,
    reconcile_kill_switch,
)

# Create NetworkPolicy that blocks non-VPN egress
config = KillSwitchConfig(
    app_name="qbittorrent",
    namespace="download-clients",
    cluster_cidrs=["10.1.0.0/16", "10.152.183.0/24"],
    dns_namespace="kube-system",
)
reconcile_kill_switch(manager, "qbittorrent", "download-clients", config)

# Remove kill switch on relation-broken
reconcile_kill_switch(manager, "qbittorrent", "download-clients", None)
```

### Constants

```python
from charmarr_lib.vpn import (
    POD_GATEWAY_IMAGE,
    DEFAULT_VXLAN_ID,
    DEFAULT_VXLAN_IP_NETWORK,
    GATEWAY_INIT_CONTAINER_NAME,
    GATEWAY_SIDECAR_CONTAINER_NAME,
    CLIENT_INIT_CONTAINER_NAME,
    CLIENT_SIDECAR_CONTAINER_NAME,
)
```

## License

LGPL-3.0-or-later
