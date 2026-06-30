"""MCP Resources: read-only snapshot URIs that LLMs can pull without a tool call.

Follows the Home Assistant built-in MCP server convention of ``homeassistant://``
URIs.
"""

from __future__ import annotations

import json

from .app import _collect_overview, client, mcp, settings
from .ha_client import HAError
from .tools.skills import _read_skill


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


@mcp.resource("homeassistant://assist/context-snapshot")
async def resource_builtin_assist_context_snapshot() -> str:
    """Proxy HA built-in MCP context snapshot when combined mode is enabled."""
    if not settings.builtin_mcp_url:
        return json.dumps(
            {
                "enabled": False,
                "message": (
                    "Combined mode is not enabled. Set HA_BUILTIN_MCP_URL to "
                    "your Home Assistant built-in MCP endpoint, usually "
                    f"{settings.ha_url.rstrip('/')}/api/mcp."
                ),
            },
            indent=2,
        )

    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        headers = {"Authorization": f"Bearer {settings.ha_token}"}
        async with streamablehttp_client(
            settings.builtin_mcp_url,
            headers=headers,
            timeout=settings.timeout,
        ) as (read_stream, write_stream, _get_session_id):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.read_resource("homeassistant://assist/context-snapshot")
        contents = []
        for item in getattr(result, "contents", []) or []:
            contents.append(
                {
                    "uri": str(getattr(item, "uri", "")),
                    "mimeType": getattr(item, "mimeType", None),
                    "text": getattr(item, "text", None),
                    "blob": getattr(item, "blob", None),
                }
            )
        return json.dumps(
            {
                "enabled": True,
                "source": settings.builtin_mcp_url,
                "contents": contents,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {
                "enabled": True,
                "source": settings.builtin_mcp_url,
                "error": str(exc),
            },
            indent=2,
        )


@mcp.resource("skill://api-reference")
async def resource_skill_api_reference() -> str:
    return _read_skill("api-reference")


@mcp.resource("skill://error-diagnosis")
async def resource_skill_error_diagnosis() -> str:
    return _read_skill("error-diagnosis")


@mcp.resource("skill://claude-link-workflow")
async def resource_skill_claude_link_workflow() -> str:
    return _read_skill("claude-link-workflow")


@mcp.resource("skill://easy-setup")
async def resource_skill_easy_setup() -> str:
    return _read_skill("easy-setup")


@mcp.resource("skill://dashboard-structure")
async def resource_skill_dashboard_structure() -> str:
    return _read_skill("dashboard-structure")
