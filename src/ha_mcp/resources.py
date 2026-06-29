"""MCP Resources: read-only snapshot URIs that LLMs can pull without a tool call.

Follows the Home Assistant built-in MCP server convention of ``homeassistant://``
URIs.
"""

from __future__ import annotations

import json

from .app import client, mcp
from .ha_client import HAError


async def _make_overview() -> str:
    """Internal: collect the same data as get_overview for the resource."""
    config = await client.rest_get("/config")
    states = await client.rest_get("/states")
    config_entries = await client.ws_command({"type": "config_entries/get"})

    entities_by_domain: dict[str, int] = {}
    automation_count = 0
    script_count = 0
    scene_count = 0
    update_pending = 0
    for s in (states if isinstance(states, list) else []):
        eid: str = s["entity_id"]
        domain = eid.partition(".")[0]
        entities_by_domain[domain] = entities_by_domain.get(domain, 0) + 1
        if domain == "automation":
            automation_count += 1
        elif domain == "script":
            script_count += 1
        elif domain == "scene":
            scene_count += 1
        elif domain == "update" and s.get("state") == "on":
            update_pending += 1

    error_count = 0
    try:
        errors = await client.ws_command({"type": "system_log/list"})
        error_count = len(errors) if isinstance(errors, list) else 0
    except Exception:
        pass

    integration_count = len(config_entries) if isinstance(config_entries, list) else 0
    integration_failed = sum(
        1 for e in (config_entries if isinstance(config_entries, list) else [])
        if e.get("state") == "not_loaded"
    )

    return json.dumps({
        "version": config.get("version") if isinstance(config, dict) else None,
        "location_name": config.get("location_name") if isinstance(config, dict) else None,
        "entities_by_domain": dict(sorted(entities_by_domain.items())),
        "automations": automation_count,
        "scripts": script_count,
        "scenes": scene_count,
        "pending_updates": update_pending,
        "errors": error_count,
        "integrations": integration_count,
        "integrations_failed": integration_failed,
    }, indent=2, ensure_ascii=False, default=str)


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
