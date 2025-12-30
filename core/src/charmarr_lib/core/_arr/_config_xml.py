# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Configuration XML utilities for *ARR applications.

All arr applications (Prowlarr, Radarr, Sonarr, Lidarr) store their
configuration in /config/config.xml including the auto-generated API key.
"""

import re
import secrets
import string


def read_api_key(config_content: str) -> str | None:
    """Extract API key from arr config.xml content.

    Args:
        config_content: The XML content of config.xml

    Returns:
        The API key string, or None if not found
    """
    match = re.search(r"<ApiKey>([^<]+)</ApiKey>", config_content)
    return match.group(1) if match else None


def config_has_api_key(config_content: str, api_key: str) -> bool:
    """Check if config.xml contains the expected API key.

    Args:
        config_content: The XML content of config.xml
        api_key: The expected API key

    Returns:
        True if config has this exact API key, False otherwise
    """
    return read_api_key(config_content) == api_key


def generate_api_key() -> str:
    """Generate a secure API key for arr applications.

    Returns:
        A 32-character lowercase alphanumeric string suitable for arr API keys
    """
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def update_api_key(config_content: str, new_api_key: str) -> str:
    """Update API key in config.xml content.

    Args:
        config_content: The XML content of config.xml
        new_api_key: The new API key to set

    Returns:
        Updated config.xml content
    """
    return re.sub(
        r"<ApiKey>[^<]*</ApiKey>",
        f"<ApiKey>{new_api_key}</ApiKey>",
        config_content,
    )


def _set_element(content: str, element: str, value: str | int) -> str:
    """Add or update an XML element."""
    pattern = rf"<{element}>[^<]*</{element}>"
    replacement = f"<{element}>{value}</{element}>"
    if re.search(pattern, content):
        return re.sub(pattern, replacement, content)
    return re.sub(r"(</Config>)", f"  {replacement}\n\\1", content)


def _remove_element(content: str, element: str) -> str:
    """Remove an XML element if it exists."""
    return re.sub(rf"\s*<{element}>[^<]*</{element}>\s*", "", content)


def reconcile_config_xml(
    content: str | None,
    *,
    api_key: str | None = None,
    url_base: str | None = None,
    port: int | None = None,
    bind_address: str | None = None,
) -> str:
    """Reconcile config.xml content idempotently.

    Creates, updates, or removes config elements based on provided values.
    Preserves all other settings (authentication, user preferences, etc.).

    Args:
        content: Existing config.xml content, or None to create fresh
        api_key: API key value, or None to remove
        url_base: URL base path, or None to remove
        port: Port number, or None to remove
        bind_address: Bind address, or None to remove

    Returns:
        Updated config.xml content
    """
    if content is None:
        content = '<?xml version="1.0" encoding="utf-8"?>\n<Config>\n</Config>\n'

    elements = {
        "ApiKey": api_key,
        "UrlBase": url_base,
        "Port": port,
        "BindAddress": bind_address,
    }

    for element, value in elements.items():
        if value is not None:
            content = _set_element(content, element, value)
        else:
            content = _remove_element(content, element)

    return content
