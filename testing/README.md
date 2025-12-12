# charmarr-lib-testing

Testing utilities for Charmarr charms.

## Features

- TFManager for Terraform-based integration testing
- pytest-bdd step definitions for common scenarios
- Testing fixtures and utilities
- jubilant integration for Juju testing

## Installation

```bash
pip install charmarr-lib-testing
```

## Usage

```python
from charmarr_lib.testing import TFManager, wait_for_active_idle
from charmarr_lib.testing.steps import common_deployment_steps
```

## License

LGPL-3.0-or-later
