"""MCP Resources: read-only snapshot URIs that LLMs can pull without a tool call.

Follows the Home Assistant built-in MCP server convention of ``homeassistant://``
URIs.
"""

from __future__ import annotations

import json

from .app import _collect_overview, client, mcp
from .ha_client import HAError


async def _make_overview() -> str:
    """Internal: collect the same data as get_overview for the resource."""
    return json.dumps(
        await _collect_overview(),
        indent=2,
        ensure_ascii=False,
        default=str,
    )


@mcp.resource("homeassistant://overview")
async def resource_overview() -> str:
    """Live snapshot of the Home Assistant installation overview."""
    try:
        return await _make_overview()
    except HAError as exc:
        return json.dumps({"error": str(exc)})


@mcp.resource("homeassistant://services")
async def resource_services() -> str:
    """List all available Home Assistant services."""
    try:
        services = await client.rest_get("/services")
        out = {}
        for s in (services if isinstance(services, list) else []):
            domain = s.get("domain", "")
            svc_names = sorted(s.get("services", {}).keys())
            out[domain] = svc_names
        return json.dumps(out, indent=2)
    except HAError as exc:
        return json.dumps({"error": str(exc)})


@mcp.resource("homeassistant://areas")
async def resource_areas() -> str:
    """List all areas and floors."""
    try:
        areas = await client.ws_command({"type": "config/area_registry/list"})
        floors = await client.ws_command({"type": "config/floor_registry/list"})
        return json.dumps({
            "areas": areas if isinstance(areas, list) else [],
            "floors": floors if isinstance(floors, list) else [],
        }, indent=2, ensure_ascii=False, default=str)
    except HAError as exc:
        return json.dumps({"error": str(exc)})


@mcp.resource("homeassistant://integrations")
async def resource_integrations() -> str:
    """List all config entries (integrations) with their state."""
    try:
        entries = await client.ws_command({"type": "config_entries/get"})
        summary = []
        for e in (entries if isinstance(entries, list) else []):
            summary.append({
                "entry_id": e.get("entry_id"),
                "domain": e.get("domain"),
                "title": e.get("title"),
                "state": e.get("state"),
                "source": e.get("source"),
            })
        return json.dumps(summary, indent=2, ensure_ascii=False, default=str)
    except HAError as exc:
        return json.dumps({"error": str(exc)})
