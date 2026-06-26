"""Supervisor features for HA OS / Supervised installs: add-ons and backups.

These go through Home Assistant's Supervisor proxy at /api/hassio/*. They only
work on HA OS / Supervised systems; on Container/Core installs they return an
error, which is surfaced to the caller.
"""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp
from ..ha_client import HAError


def _data(resp: Any) -> Any:
    """Supervisor responses are wrapped as {"result": "ok", "data": {...}}."""
    if isinstance(resp, dict) and "data" in resp:
        return resp["data"]
    return resp


# -------------------------------------------------------------------- add-ons
@mcp.tool()
async def list_addons() -> str:
    """List installed add-ons (HA OS / Supervised only)."""
    return _dump(_data(await client.rest_get("/hassio/addons")))


@mcp.tool()
async def get_addon_info(slug: str) -> str:
    """Get detailed info/state for an add-on by slug (e.g. 'core_mosquitto')."""
    return _dump(_data(await client.rest_get(f"/hassio/addons/{slug}/info")))


@mcp.tool()
async def control_addon(slug: str, action: str) -> str:
    """Control an add-on. action is one of: start, stop, restart, update, rebuild."""
    allowed = {"start", "stop", "restart", "update", "rebuild"}
    if action not in allowed:
        raise HAError(f"Unknown add-on action {action!r}. Allowed: {sorted(allowed)}")
    return _dump(_data(await client.rest_post(f"/hassio/addons/{slug}/{action}", {})))


@mcp.tool()
async def get_addon_logs(slug: str) -> str:
    """Get the recent logs for an add-on."""
    return _dump(await client.rest_get(f"/hassio/addons/{slug}/logs"))


# -------------------------------------------------------------------- backups
@mcp.tool()
async def list_backups() -> str:
    """List existing backups (HA OS / Supervised only)."""
    return _dump(_data(await client.rest_get("/hassio/backups")))


@mcp.tool()
async def create_backup(name: str | None = None, full: bool = True) -> str:
    """Create a backup. By default a full backup; set full=False for a minimal
    (partial) backup of just the HA config folder."""
    body: dict[str, Any] = {}
    if name:
        body["name"] = name
    endpoint = "/hassio/backups/new/full" if full else "/hassio/backups/new/partial"
    if not full:
        body.setdefault("folders", ["homeassistant"])
    return _dump(_data(await client.rest_post(endpoint, body)))


# ------------------------------------------------------------ host / sup info
@mcp.tool()
async def supervisor_info() -> str:
    """Get Supervisor info (version, add-ons summary, diagnostics)."""
    return _dump(_data(await client.rest_get("/hassio/supervisor/info")))


@mcp.tool()
async def host_info() -> str:
    """Get host info (OS, disk usage, hostname) for HA OS / Supervised."""
    return _dump(_data(await client.rest_get("/hassio/host/info")))
