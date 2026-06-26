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

settings = load_settings()
client = HAClient(settings)
mcp = FastMCP("home-assistant")

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
