# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""NetBird Management API constants."""

# Management REST API.
API_BASE_PATH = "/api"
API_AUTH_SCHEME = "Token"  # Authorization: Token <pat>

# Least-privilege role for per-registration service users (ADR-0010 spike).
# network_admin can CRUD Networks/Resources/Routers/Policies/Routes/Groups/DNS/PATs
# but is READ-ONLY on Setup Keys, so the owner PAT must mint setup keys.
NETWORK_ADMIN_ROLE = "network_admin"

# Personal access tokens cap at 365 days; tokens must be rotated before expiry.
MAX_TOKEN_EXPIRY_DAYS = 365
