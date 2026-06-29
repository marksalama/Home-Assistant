"""Automation / script blueprints: list, inspect and import."""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp


@mcp.tool()
async def list_blueprints(domain: str = "automation") -> str:
    """List all blueprints for a domain (automation or script).

    Args:
        domain: "automation" (default) or "script".
    """
    return _dump(await client.ws_command({"type": "blueprint/list", "domain": domain}))


@mcp.tool()
async def get_blueprint(domain: str, blueprint_path: str) -> str:
    """Get a blueprint's full definition. `blueprint_path` comes from
    list_blueprints (e.g. "homeassistant/confirmable_notification.yaml").

    Args:
        domain: "automation" or "script".
        blueprint_path: Path relative to the blueprint namespace.
    """
    return _dump(await client.ws_command({
        "type": "blueprint/get",
        "domain": domain,
        "path": blueprint_path,
    }))


@mcp.tool()
async def import_blueprint(url: str) -> str:
    """Import a blueprint by URL (community forum GitHub, etc.). Automations
    imported this way become available in the UI automation editor blueprint
    picker.

    Args:
        url: Full URL to the blueprint's raw YAML.
    """
    return _dump(await client.ws_command({
        "type": "blueprint/import",
        "url": url,
    }))
