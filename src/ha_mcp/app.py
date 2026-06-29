"""Shared application objects: settings, HA client, the FastMCP instance and
small helpers. Tool modules import from here and register themselves.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_settings
from .files import FilesDisabledError, get_backend
from .ha_client import HAClient
from .snapshots import SnapshotStore

INSTRUCTIONS = """\
This server gives you broad control over a Home Assistant installation. Follow
these conventions so tools are used correctly and efficiently.

DISCOVERY (be token-efficient):
- Use get_overview for a one-call summary of the entire installation.
- Use fuzzy_search to find entities by name, area, or label (better than
  listing everything and filtering yourself).
- list_entities(domain=..., search=..., fields=...) supports field projection
  to reduce token usage — pass fields="entity_id,state" for compact results.
- For one entity's full picture use get_state (with attribute_keys= to project),
  or diagnose_entity for debugging (state + registry + device in one call).
- list_areas / list_devices / list_entity_registry / list_labels for structure.

CONTROLLING DEVICES:
- Use call_service(domain, service, data) for actions. Target with entity_id,
  area_id, device_id or label_id (so one call can act on a whole room).
- Use bulk_control(service, targets, data) to call a service for multiple
  targets in parallel (e.g. turn off all lights in several rooms at once).
- set_state only changes HA's state machine; it does NOT command a device.

CONFIGURING (automations/scripts/scenes/helpers):
- Prefer the dedicated tools: upsert_automation/script/scene (they reload
  automatically), and create/update/delete_helper. Read the current config with
  get_automation/get_script/get_scene before editing.
- Use list_blueprints and import_blueprint to work with automation blueprints.
- Use list_automation_traces and get_automation_trace to debug why an automation
  misbehaved (shows every step, condition evaluation and action result).

CALENDAR & TODO:
- list_calendars / get_calendar_events for reading calendar events.
- create/update/remove_calendar_event for managing events.
- list_todo_lists / get_todo_items / add_todo_item for to-do lists.

YAML EDITING (safe & reversible):
- read_config_file before write_config_file. Writes auto-snapshot the previous
  version; undo with restore_config_file (list_file_snapshots to see versions).
- Use set_yaml_key for structured edits (add/replace/remove one top-level key
  with automatic validation). Safer than raw write_config_file for simple edits.
- After editing core YAML: run check_config, then reload_domain(...) if possible,
  otherwise restart_home_assistant(confirm=True). Never restart without checking.

SAFETY:
- Destructive tools require confirm=True (restart, reboot, delete_*, install_update,
  uninstall_addon, restore_backup). Consider create_backup before big changes.
- If a tool raises a read-only error, the user enabled HA_READ_ONLY; ask them to
  disable it for changes.

HA OS ONLY: add-on and backup tools (list_addons, control_addon, *_backup,
host/supervisor tools) only work on HA OS / Supervised; they error otherwise.

DEBUGGING: get_error_log (system_log entries), get_core_logs/get_supervisor_logs/
get_addon_logs, set_log_level(integration, "debug"), system_health,
list_automation_traces + get_automation_trace.

ENTITY EXPOSURE: get_entity_exposure / set_entity_exposure to control which
entities are exposed to Assist (conversation), Alexa (cloud.alexa), or
Google Assistant (cloud.google_assistant).
"""

settings = load_settings()
client = HAClient(settings)
mcp = FastMCP("home-assistant", instructions=INSTRUCTIONS)

# Local snapshot store for reversible file edits (None if disabled).
snapshots = SnapshotStore(settings.snapshot_dir) if settings.snapshots_enabled else None

# Helper storage-collection domains that share the same WS list/create/update/delete API.
HELPER_DOMAINS = {
    "input_boolean",
    "input_button",
    "input_number",
    "input_text",
    "input_select",
    "input_datetime",
    "counter",
    "timer",
    "schedule",
}

# --------------------------------------------------------------------------
# Activity heartbeat -> optional `claude_link` Home Assistant integration.
# Every tool returns through `_dump`, so we use it as a single chokepoint to
# (a) count tool calls and (b) lazily start a background heartbeat task that
# reports liveness to HA. Everything here fails silently if the integration
# isn't installed.
# --------------------------------------------------------------------------
TOOL_CALLS = 0
_heartbeat_started = False


async def _heartbeat_loop() -> None:
    while True:
        try:
            await client.rest_post(
                "/services/claude_link/report",
                {"tool_calls": TOOL_CALLS, "source": "claude-code"},
                write=False,
            )
        except Exception:
            pass  # integration not installed or HA unreachable; ignore
        await asyncio.sleep(30)


def _ensure_heartbeat() -> None:
    global _heartbeat_started
    if _heartbeat_started:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _heartbeat_started = True
    loop.create_task(_heartbeat_loop())


def _dump(data: Any) -> str:
    global TOOL_CALLS
    TOOL_CALLS += 1
    _ensure_heartbeat()
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _files():
    backend = get_backend(settings)
    if backend is None:
        raise FilesDisabledError(
            "Raw file access is disabled. Set HA_FILES_BACKEND to 'local' or 'ssh' "
            "(see .env.example) to read/write configuration files."
        )
    return backend


def _apply_tool_filter() -> None:
    """Remove disabled tools / only keep enabled tools on the shared FastMCP
    instance. Called after all tool modules have been imported."""
    all_names = list(mcp._tool_manager._tools.keys())
    if settings.enabled_tools is not None:
        for name in all_names:
            if name not in settings.enabled_tools:
                mcp._tool_manager.remove_tool(name)
    elif settings.disabled_tools:
        for name in settings.disabled_tools:
            if name in mcp._tool_manager._tools:
                mcp._tool_manager.remove_tool(name)
