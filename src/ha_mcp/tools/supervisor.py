"""Supervisor features for HA OS / Supervised installs: add-ons, backups, logs.

These go through Home Assistant's Supervisor proxy at /api/hassio/*. They only
work on HA OS / Supervised systems; on Container/Core installs they return an
error, which is surfaced to the caller.
"""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, settings, mcp
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
async def list_available_addons() -> str:
    """List all add-ons available in the store (installed and not installed)."""
    data = _data(await client.rest_get("/hassio/store"))
    addons = data.get("addons", data) if isinstance(data, dict) else data
    slim = [
        {"slug": a.get("slug"), "name": a.get("name"), "version": a.get("version"),
         "installed": a.get("installed"), "description": a.get("description")}
        for a in addons
    ]
    return _dump({"count": len(slim), "addons": slim})


@mcp.tool()
async def get_addon_info(slug: str) -> str:
    """Get detailed info/state for an add-on by slug (e.g. 'core_mosquitto')."""
    return _dump(_data(await client.rest_get(f"/hassio/addons/{slug}/info")))


@mcp.tool()
async def get_addon_stats(slug: str) -> str:
    """Get live resource usage (CPU, memory, network) for a running add-on."""
    return _dump(_data(await client.rest_get(f"/hassio/addons/{slug}/stats")))


@mcp.tool()
async def get_addon_changelog(slug: str) -> str:
    """Get the changelog for an add-on (useful before updating)."""
    return _dump(await client.rest_get(f"/hassio/addons/{slug}/changelog"))


@mcp.tool()
async def control_addon(slug: str, action: str, backup: bool | None = None) -> str:
    """Control an add-on.

    Args:
        slug: Add-on slug, e.g. 'core_mosquitto'.
        action: one of start, stop, restart, update, rebuild.
        backup: For 'update', whether to create a backup first. Defaults to the
            HA_AUTO_BACKUP_BEFORE_UPDATE setting.
    """
    allowed = {"start", "stop", "restart", "update", "rebuild"}
    if action not in allowed:
        raise HAError(f"Unknown add-on action {action!r}. Allowed: {sorted(allowed)}")
    body: dict[str, Any] = {}
    if action == "update":
        do_backup = settings.auto_backup_before_update if backup is None else backup
        if do_backup:
            body["backup"] = True
    return _dump(_data(await client.rest_post(f"/hassio/addons/{slug}/{action}", body)))


@mcp.tool()
async def install_addon(slug: str) -> str:
    """Install an add-on from the store by slug."""
    return _dump(_data(await client.rest_post(f"/hassio/store/addons/{slug}/install", {})))


@mcp.tool()
async def uninstall_addon(slug: str, confirm: bool = False) -> str:
    """Uninstall an add-on. Requires confirm=True."""
    if not confirm:
        raise HAError("Refusing to uninstall an add-on without confirm=True.")
    return _dump(_data(await client.rest_post(f"/hassio/addons/{slug}/uninstall", {})))


@mcp.tool()
async def set_addon_options(slug: str, options: dict) -> str:
    """Set an add-on's configuration options. `options` is merged into the
    add-on's existing config (validated by the add-on schema)."""
    return _dump(_data(await client.rest_post(f"/hassio/addons/{slug}/options", {"options": options})))


@mcp.tool()
async def get_addon_logs(slug: str) -> str:
    """Get the recent logs for an add-on (debugging)."""
    return _dump(await client.rest_get(f"/hassio/addons/{slug}/logs"))


# ---------------------------------------------------------------------- logs
@mcp.tool()
async def get_core_logs() -> str:
    """Get the Home Assistant Core logs via Supervisor (debugging)."""
    return _dump(await client.rest_get("/hassio/core/logs"))


@mcp.tool()
async def get_supervisor_logs() -> str:
    """Get the Supervisor logs (debugging)."""
    return _dump(await client.rest_get("/hassio/supervisor/logs"))


@mcp.tool()
async def get_host_logs() -> str:
    """Get the host system logs (debugging)."""
    return _dump(await client.rest_get("/hassio/host/logs"))


# -------------------------------------------------------------------- backups
@mcp.tool()
async def list_backups() -> str:
    """List existing backups (HA OS / Supervised only)."""
    return _dump(_data(await client.rest_get("/hassio/backups")))


@mcp.tool()
async def create_backup(name: str | None = None, full: bool = True) -> str:
    """Create a backup. By default a full backup; set full=False for a minimal
    (partial) backup of just the HA config folder. Returns the backup slug."""
    body: dict[str, Any] = {}
    if name:
        body["name"] = name
    endpoint = "/hassio/backups/new/full" if full else "/hassio/backups/new/partial"
    if not full:
        body.setdefault("folders", ["homeassistant"])
    return _dump(_data(await client.rest_post(endpoint, body)))


@mcp.tool()
async def restore_backup(slug: str, confirm: bool = False, full: bool = True) -> str:
    """Restore a backup by slug. Requires confirm=True. This reverts Home
    Assistant to the state captured in that backup (a key rollback tool)."""
    if not confirm:
        raise HAError("Refusing to restore a backup without confirm=True.")
    endpoint = f"/hassio/backups/{slug}/restore/{'full' if full else 'partial'}"
    body: dict[str, Any] = {} if full else {"folders": ["homeassistant"]}
    return _dump(_data(await client.rest_post(endpoint, body)))


@mcp.tool()
async def delete_backup(slug: str, confirm: bool = False) -> str:
    """Delete a backup by slug. Requires confirm=True."""
    if not confirm:
        raise HAError("Refusing to delete a backup without confirm=True.")
    return _dump(_data(await client.rest_delete(f"/hassio/backups/{slug}")))


# ------------------------------------------------------------ host / sup info
@mcp.tool()
async def supervisor_info() -> str:
    """Get Supervisor info (version, add-ons summary, diagnostics)."""
    return _dump(_data(await client.rest_get("/hassio/supervisor/info")))


@mcp.tool()
async def host_info() -> str:
    """Get host info (OS, disk usage, hostname) for HA OS / Supervised."""
    return _dump(_data(await client.rest_get("/hassio/host/info")))


@mcp.tool()
async def update_supervisor() -> str:
    """Update the Supervisor itself to the latest version."""
    return _dump(_data(await client.rest_post("/hassio/supervisor/update", {})))


@mcp.tool()
async def reboot_host(confirm: bool = False) -> str:
    """Reboot the host machine (HA OS). Requires confirm=True."""
    if not confirm:
        raise HAError("Refusing to reboot the host without confirm=True.")
    return _dump(_data(await client.rest_post("/hassio/host/reboot", {})))
