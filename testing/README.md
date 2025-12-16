<p align="center">
  <img src="../assets/charmarr-charmarr-lib.png" width="350" alt="Charmarr Lib">
</p>

<h1 align="center">charmarr-lib-testing</h1>

Testing utilities for Charmarr charms.

## Features

- TFManager for Terraform/OpenTofu-based integration testing
- Jubilant integration for Juju model stabilization
- Minimal, focused utilities (step definitions added as patterns emerge)

## Installation

```bash
pip install charmarr-lib-testing
```

## Usage

### TFManager

Wrapper around Terraform/OpenTofu for integration tests. Prefers OpenTofu if available.

```python
from pathlib import Path
from charmarr_lib.testing import TFManager

# Initialize with terraform directory
tf = TFManager(Path("./terraform"))
tf.init()

# Apply with environment variables (e.g., for Juju credentials)
tf.apply(env={"TF_VAR_model_name": "my-model"})

# Get outputs
model_name = tf.output("model_name")

# Cleanup
tf.destroy(env={"TF_VAR_model_name": "my-model"})
```

### wait_for_active_idle

Wait for Juju models to stabilize after deployment.

```python
from charmarr_lib.testing import wait_for_active_idle
import jubilant

# Single model
juju = jubilant.Juju()
wait_for_active_idle(juju, timeout=60 * 20)  # 20 minutes

# Multiple models (e.g., cross-model relations)
jujus = [jubilant.Juju(model="model-a"), jubilant.Juju(model="model-b")]
wait_for_active_idle(jujus)
```

The function:
1. Waits for all units to be active (with 3 consecutive successes)
2. Checks for any errors
3. Waits for all agents to be idle
