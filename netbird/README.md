<h1 align="center">charmarr-lib-netbird</h1>

Shared library for the NetBird charm suite.

## Contents

- NetBird relation interfaces (Provider/Requirer pairs)
- NetBird Management REST API client
- Shared constants

## Installation

```bash
pip install charmarr-lib-netbird
```

## Usage

### Interfaces

```python
from charmarr_lib.netbird.interfaces import (
    NetbirdEnrollmentProvider,
    NetbirdEnrollmentRequirer,
    NetbirdEnrollmentProviderData,
    NetbirdEnrollmentRequirerData,
    NetbirdEnrollmentCredentials,
)
```

### Management API client

```python
from charmarr_lib.netbird import NetbirdManagementClient

with NetbirdManagementClient("https://netbird.example.com", api_token) as client:
    user = client.create_service_user("router-a")
    token = client.create_user_token(user.id, "router-a", expires_in=365)
    key = client.create_setup_key("router-a")
```
