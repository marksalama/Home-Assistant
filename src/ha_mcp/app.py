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
- To find entities, use list_entities(domain=..., search=...) with filters
  instead of dumping everything. Domains: light, switch, sensor, climate, etc.
- For one entity's full picture use get_state, or diagnose_entity for debugging
  (state + registry + device in one call).
- list_areas / list_devices / list_entity_registry / list_labels for structure.

CONTROLLING DEVICES:
- Use call_service(domain, service, data) for actions. Target with entity_id,
  area_id, device_id or label_id (so one call can act on a whole room).
- set_state only changes HA's state machine; it does NOT command a device.

CONFIGURING (automations/scripts/scenes/helpers):
- Prefer the dedicated tools: upsert_automation/script/scene (they reload
  automatically), and create/update/delete_helper. Read the current config with
  get_automation/get_script/get_scene before editing.

EDITING RAW YAML (safe & reversible):
- read_config_file before write_config_file. Writes auto-snapshot the previous
  version; undo with restore_config_file (list_file_snapshots to see versions).
- After editing core YAML: run check_config, then reload_domain(...) if possible,
  otherwise restart_home_assistant(confirm=True). Never restart without checking.

SAFETY:
- Destructive tools require confirm=True (restart, reboot, delete_*, install_update,
  uninstall_addon, restore_backup). Consider create_backup before big changes.
- If a tool raises a read-only error, the user enabled HA_READ_ONLY; ask them to
  disable it for changes.

HA OS ONLY: add-on and backup tools (list_addons, control_addon, *_backup,
host/supervisor tools) only work on HA OS / Supervised; they error otherwise.

DEBUGGING: get_error_log, get_core_logs/get_supervisor_logs/get_addon_logs,
set_log_level(integration, "debug"), system_health.
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
