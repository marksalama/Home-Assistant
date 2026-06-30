"""Tool discovery: search-based tool retrieval for smaller / local LLMs.

When ``HA_ENABLE_TOOL_SEARCH=true``, the full tool catalog is replaced with four
discovery entry points plus a small set of pinned tools. All tools remain
directly callable by name once discovered.
"""

from __future__ import annotations

import os
import re
from typing import Any

from ..app import _dump, mcp, settings
from ..ha_client import HAError

# ---------------------------------------------------------------------------
# Tool annotations — classify every tool as read, write, or delete so the
# discovery proxy tools can route correctly.
# ---------------------------------------------------------------------------
_READ_TOOLS = {
    "list_entities", "get_state", "list_services",
    "list_automations", "get_automation",
    "list_scripts", "get_script",
    "list_scenes", "get_scene",
    "list_dashboards", "get_dashboard",
    "list_config_files", "read_config_file", "list_file_snapshots",
    "list_helpers",
    "list_areas", "list_floors", "list_devices", "list_entity_registry",
    "list_labels", "get_label", "list_persons", "list_zones", "get_zone",
    "list_config_entries",
    "list_addons", "list_available_addons", "get_addon_info", "get_addon_stats",
    "get_addon_changelog", "get_addon_logs",
    "get_core_logs", "get_supervisor_logs", "get_host_logs",
    "get_config", "check_config", "system_health",
    "render_template", "get_history", "get_logbook", "get_error_log",
    "get_statistics",
    "list_backups", "supervisor_info", "host_info",
    "get_energy_prefs",
    "list_updates",
    "list_notifications",
    "get_automation_traces", "get_automation_trace",
    "get_blueprint", "list_blueprints",
    "list_calendars", "get_calendar_events",
    "get_camera_image",
    "get_todo_items", "list_todo_lists",
    "list_groups",
    "get_overview", "fuzzy_search",
    "get_entity_exposure",
    "diagnose_entity",
    "list_themes",
    "get_mcp_install_options",
    "report_issue",
    "get_skill_guide",
    "get_hacs_info",
}

_DELETE_TOOLS = {
    "delete_automation",
    "delete_script",
    "delete_scene",
    "delete_config_file",
    "delete_helper",
    "delete_area", "delete_floor", "remove_device", "remove_entity",
    "delete_label",
    "delete_config_entry",
    "uninstall_addon",
    "delete_backup",
    "dismiss_notification",
    "delete_automation_trace",
    "remove_calendar_event",
    "remove_todo_item",
    "remove_group",
    "delete_zone",
    "remove_person",
}

# Everything that is not read or delete is "write" (create/update/set/control)
_WRITE_TOOLS = set()

def _classify_tools() -> None:
    """Fill _WRITE_TOOLS with all tools not in read or delete sets."""
    all_names = set(mcp._tool_manager._tools.keys())
    known = _READ_TOOLS | _DELETE_TOOLS
    for name in all_names:
        if name not in known:
            _WRITE_TOOLS.add(name)


# Proxy tools are meta-tools — add them to the appropriate sets so the
# classifier doesn't leave them unclassified.
_READ_TOOLS.add("search_tools")
_READ_TOOLS.add("call_read_tool")
_WRITE_TOOLS.add("call_write_tool")
_DELETE_TOOLS.add("call_delete_tool")


def _annotation_for(name: str) -> dict[str, str]:
    if name in _READ_TOOLS:
        return {"readOnlyHint": "true"}
    if name in _DELETE_TOOLS:
        return {"destructiveHint": "true"}
    if name in _WRITE_TOOLS:
        return {"idempotentHint": "true"}
    return {}


def _pinned_tools() -> set[str]:
    env = os.environ.get("HA_PINNED_TOOLS", "")
    return {t.strip() for t in env.split(",") if t.strip()}


def _token_overlap(query: str, text: str) -> int:
    """Simple token-overlap score (0-N where N = number of query tokens)."""
    q_tokens = query.lower().split()
    t = text.lower()
    return sum(1 for tok in q_tokens if tok in t)


def _search_tools(query: str, max_results: int) -> list[dict[str, Any]]:
    """Score all registered tools against the query and return top results."""
    results: list[dict[str, Any]] = []
    for name, tool in sorted(mcp._tool_manager._tools.items()):
        if name in ("search_tools", "call_read_tool", "call_write_tool", "call_delete_tool"):
            continue
        desc = getattr(tool, "description", "") or ""
        score = _token_overlap(query, f"{name} {desc}")
        if score > 0:
            results.append({
                "name": name,
                "description": desc,
                "score": score,
                "annotations": _annotation_for(name),
            })
    results.sort(key=lambda r: (r["score"], r["name"]), reverse=True)
    return results[:max_results]


# --------------------------------------------------------------------
@mcp.tool()
async def search_tools(query: str, max_results: int = 5) -> str:
    """Search available tools by keyword (BM25-style token overlap).

    Returns matching tools with name, description, parameters, and annotations
    (readOnlyHint / destructiveHint). Use the results to pick the right tool,
    then call it via ``call_read_tool``, ``call_write_tool`` or
    ``call_delete_tool``.
    """
    max_results = max(2, min(max_results, 10))
    matches = _search_tools(query, max_results)
    # enrich with parameter info
    for m in matches:
        tool = mcp._tool_manager._tools.get(m["name"])
        if tool and hasattr(tool, "parameters"):
            params = getattr(tool, "parameters", None)
            if params:
                m["parameters"] = params
    return _dump({"query": query, "results": matches})


@mcp.tool()
async def call_read_tool(name: str, arguments: dict | None = None) -> str:
    """Call a read-only tool by name with the given arguments.

    Args:
        name: Exact tool name from search_tools results.
        arguments: Tool arguments as a dict.
    """
    if name not in mcp._tool_manager._tools:
        raise HAError(f"Unknown tool: {name!r}. Use search_tools to find the right one.")
    if name not in _READ_TOOLS:
        raise HAError(f"{name!r} is not a read-only tool. Use call_write_tool or call_delete_tool instead.")
    result = await mcp._tool_manager.call_tool(name, arguments or {})
    return _dump(result)


@mcp.tool()
async def call_write_tool(name: str, arguments: dict | None = None) -> str:
    """Call a write (create/update) tool by name with the given arguments.

    Args:
        name: Exact tool name from search_tools results.
        arguments: Tool arguments as a dict.
    """
    if name not in mcp._tool_manager._tools:
        raise HAError(f"Unknown tool: {name!r}. Use search_tools to find the right one.")
    if name not in _WRITE_TOOLS:
        if name in _READ_TOOLS:
            raise HAError(f"{name!r} is a read-only tool. Use call_read_tool instead.")
        if name in _DELETE_TOOLS:
            raise HAError(f"{name!r} is a delete tool. Use call_delete_tool instead.")
    result = await mcp._tool_manager.call_tool(name, arguments or {})
    return _dump(result)


@mcp.tool()
async def call_delete_tool(name: str, arguments: dict | None = None) -> str:
    """Call a delete/remove tool by name with the given arguments.

    Args:
        name: Exact tool name from search_tools results.
        arguments: Tool arguments as a dict.
    """
    if name not in mcp._tool_manager._tools:
        raise HAError(f"Unknown tool: {name!r}. Use search_tools to find the right one.")
    if name not in _DELETE_TOOLS:
        if name in _READ_TOOLS:
            raise HAError(f"{name!r} is a read-only tool. Use call_read_tool instead.")
        if name in _WRITE_TOOLS:
            raise HAError(f"{name!r} is a write tool. Use call_write_tool instead.")
    result = await mcp._tool_manager.call_tool(name, arguments or {})
    return _dump(result)


# --------------------------------------------------------------------------
# Tool-discovery mode: when enabled, replace the full tool catalog with the
# discovery entry points + pinned tools. Called after all tools are registered.
# --------------------------------------------------------------------------
def _enable_tool_search_mode() -> None:
    """Hide all tools except discovery entry points and pinned tools."""
    pinned = _pinned_tools()
    discovery_tools = {"search_tools", "call_read_tool", "call_write_tool", "call_delete_tool"}
    keep = discovery_tools | pinned

    _classify_tools()

    all_names = list(mcp._tool_manager._tools.keys())
    for name in all_names:
        if name not in keep:
            mcp._tool_manager.remove_tool(name)
