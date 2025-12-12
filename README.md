# Charmarr Library Monorepo

Shared libraries for Charmarr charms implementing Juju relations and reconcilers, distributed as three pip-installable packages from a single monorepo.

## Packages

- **charmarr-lib-core** - Core interfaces, API clients, and reconcilers
- **charmarr-lib-vpn** - VPN gateway interface and pod-gateway integration
- **charmarr-lib-testing** - Testing utilities and pytest-bdd step definitions

## Installation

```bash
pip install charmarr-lib-core
pip install charmarr-lib-vpn
pip install charmarr-lib-testing
```

## Development

```bash
# Create and activate virtual environment
uv venv && source .venv/bin/activate

# Install dependencies
uv sync

# Run all checks
tox
```

## License

LGPL-3.0-or-later
