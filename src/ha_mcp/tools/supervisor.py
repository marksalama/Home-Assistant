"""Supervisor features for HA OS / Supervised installs: add-ons, backups, logs.

These go through Home Assistant's Supervisor proxy at /api/hassio/*, with a
WebSocket `supervisor/api` fallback for HA OS installs where long-lived tokens
cannot call /api/hassio directly. On Container/Core installs they return an
error, which is surfaced to the caller.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..app import _dump, client, settings, mcp
from ..files import get_backend
from ..ha_client import HAError, ReadOnlyError

_TEXT_SUPERVISOR_ENDPOINTS = (
    "/core/logs",
    "/supervisor/logs",
    "/host/logs",
)


def _data(resp: Any) -> Any:
    """Supervisor responses are wrapped as {"result": "ok", "data": {...}}."""
    if isinstance(resp, dict) and "data" in resp:
        return resp["data"]
    return resp


def _guard_supervisor_write(method: str, endpoint: str) -> None:
    if method.lower() != "get" and settings.read_only:
        raise ReadOnlyError(
            "Server is in read-only mode (HA_READ_ONLY=true); "
            f"refusing Supervisor {method.upper()} {endpoint}"
        )


async def _supervisor_api(method: str, endpoint: str, body: dict | None = None) -> Any:
    """Call Supervisor via REST, with WebSocket fallback for HA OS tokens."""
    method = method.lower()
    endpoint = "/" + endpoint.strip("/")
    _guard_supervisor_write(method, endpoint)

    rest_path = "/hassio" + endpoint
    try:
        if method == "get":
            return _data(await client.rest_get(rest_path))
        if method == "post":
            return _data(await client.rest_post(rest_path, body or {}))
        if method == "delete":
            return _data(await client.rest_delete(rest_path))
    except HAError as exc:
        if "HTTP 401" not in str(exc):
            raise
        if method == "get" and (
            endpoint in _TEXT_SUPERVISOR_ENDPOINTS or endpoint.endswith("/logs")
        ):
            raise HAError(
                f"Supervisor text endpoint {endpoint} is not available through "
                "the Home Assistant long-lived token REST path, and the "
                "WebSocket Supervisor fallback cannot proxy text/plain log "
                "responses without causing Home Assistant log errors."
            ) from exc

    cmd: dict[str, Any] = {
        "type": "supervisor/api",
        "endpoint": endpoint,
        "method": method,
    }
    if body is not None:
        cmd["data"] = body
    return await client.ws_command(cmd)


def _read_config_log_file(tail_lines: int = 400) -> dict[str, Any]:
    backend = get_backend(settings)
    if backend is None:
        raise HAError("Raw file access is disabled; cannot read /config/home-assistant.log.")
    text = backend.read("home-assistant.log")
    lines = text.splitlines()
    return {
        "source": "home-assistant.log",
        "tail_lines": min(tail_lines, len(lines)),
        "log": "\n".join(lines[-tail_lines:]),
    }


# -------------------------------------------------------------------- add-ons
@mcp.tool()
async def list_addons() -> str:
    """List installed add-ons (HA OS / Supervised only)."""
    return _dump(await _supervisor_api("get", "/addons"))


@mcp.tool()
async def list_available_addons() -> str:
    """List all add-ons available in the store (installed and not installed)."""
    data = await _supervisor_api("get", "/store")
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
    return _dump(await _supervisor_api("get", f"/addons/{slug}/info"))


@mcp.tool()
async def get_addon_stats(slug: str) -> str:
    """Get live resource usage (CPU, memory, network) for a running add-on."""
    return _dump(await _supervisor_api("get", f"/addons/{slug}/stats"))


@mcp.tool()
async def get_addon_changelog(slug: str) -> str:
    """Get the changelog for an add-on (useful before updating)."""
    return _dump(await _supervisor_api("get", f"/addons/{slug}/changelog"))


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
    return _dump(await _supervisor_api("post", f"/addons/{slug}/{action}", body))


@mcp.tool()
async def install_addon(slug: str) -> str:
    """Install an add-on from the store by slug."""
    return _dump(await _supervisor_api("post", f"/store/addons/{slug}/install", {}))


@mcp.tool()
async def uninstall_addon(slug: str, confirm: bool = False) -> str:
    """Uninstall an add-on. Requires confirm=True."""
    if not confirm:
        raise HAError("Refusing to uninstall an add-on without confirm=True.")
    return _dump(await _supervisor_api("post", f"/addons/{slug}/uninstall", {}))


@mcp.tool()
async def set_addon_options(slug: str, options: dict) -> str:
    """Set an add-on's configuration options. `options` is merged into the
    add-on's existing config (validated by the add-on schema)."""
    return _dump(await _supervisor_api("post", f"/addons/{slug}/options", {"options": options}))


@mcp.tool()
async def get_addon_logs(slug: str) -> str:
    """Get the recent logs for an add-on (debugging)."""
    return _dump(await _supervisor_api("get", f"/addons/{slug}/logs"))


# ---------------------------------------------------------------------- logs
@mcp.tool()
async def get_core_logs() -> str:
    """Get the Home Assistant Core logs via Supervisor (debugging)."""
    try:
        return _dump(await _supervisor_api("get", "/core/logs"))
    except HAError as exc:
        try:
            return _dump(_read_config_log_file())
        except Exception:
            raise exc


@mcp.tool()
async def get_supervisor_logs() -> str:
    """Get the Supervisor logs (debugging)."""
    return _dump(await _supervisor_api("get", "/supervisor/logs"))


@mcp.tool()
async def get_host_logs() -> str:
    """Get the host system logs (debugging)."""
    return _dump(await _supervisor_api("get", "/host/logs"))


# -------------------------------------------------------------------- backups
@mcp.tool()
async def list_backups() -> str:
    """List existing backups (HA OS / Supervised only)."""
    return _dump(await _supervisor_api("get", "/backups"))


@mcp.tool()
async def create_backup(name: str | None = None, full: bool = True) -> str:
    """Create a backup. By default a full backup; set full=False for a minimal
    (partial) backup of just the HA config folder. Returns the backup slug."""
    backup_name = name or "Claude Code backup " + datetime.now().strftime("%Y-%m-%d %H:%M")
    services = await client.rest_get("/services")
    hassio_services = next(
        (
            service.get("services", {})
            for service in services
            if service.get("domain") == "hassio"
        ),
        {},
    )
    backup_services = next(
        (
            service.get("services", {})
            for service in services
            if service.get("domain") == "backup"
        ),
        {},
    )

    if full and "backup_full" in hassio_services:
        result = await client.rest_post(
            "/services/hassio/backup_full",
            {"name": backup_name, "compressed": True},
        )
        return _dump(
            {
                "ok": True,
                "method": "hassio.backup_full",
                "name": backup_name,
                "result": result,
                "note": "Backup creation was started through the HA OS/Supervisor service.",
            }
        )

    if not full and "backup_partial" in hassio_services:
        result = await client.rest_post(
            "/services/hassio/backup_partial",
            {
                "name": backup_name,
                "homeassistant": True,
                "folders": ["homeassistant"],
                "compressed": True,
            },
        )
        return _dump(
            {
                "ok": True,
                "method": "hassio.backup_partial",
                "name": backup_name,
                "result": result,
                "note": "Partial backup creation was started through the HA OS/Supervisor service.",
            }
        )

    if full and "create_automatic" in backup_services:
        try:
            result = await client.rest_post("/services/backup/create_automatic", {})
            return _dump(
                {
                    "ok": True,
                    "method": "backup.create_automatic",
                    "result": result,
                    "note": "Home Assistant did not return a backup slug for this service.",
                }
            )
        except HAError as exc:
            if "At least one available backup agent must be selected" in str(exc):
                raise HAError(
                    "backup.create_automatic is available but no backup agent is selected "
                    "in Home Assistant. Configure a backup location/agent or use HA OS "
                    "Supervisor backup services."
                ) from exc
            raise

    body: dict[str, Any] = {}
    if backup_name:
        body["name"] = backup_name
    endpoint = "/backups/new/full" if full else "/backups/new/partial"
    if not full:
        body.setdefault("folders", ["homeassistant"])
    return _dump(await _supervisor_api("post", endpoint, body))


@mcp.tool()
async def restore_backup(slug: str, confirm: bool = False, full: bool = True) -> str:
    """Restore a backup by slug. Requires confirm=True. This reverts Home
    Assistant to the state captured in that backup (a key rollback tool)."""
    if not confirm:
        raise HAError("Refusing to restore a backup without confirm=True.")
    endpoint = f"/backups/{slug}/restore/{'full' if full else 'partial'}"
    body: dict[str, Any] = {} if full else {"folders": ["homeassistant"]}
    return _dump(await _supervisor_api("post", endpoint, body))


@mcp.tool()
async def delete_backup(slug: str, confirm: bool = False) -> str:
    """Delete a backup by slug. Requires confirm=True."""
    if not confirm:
        raise HAError("Refusing to delete a backup without confirm=True.")
    return _dump(await _supervisor_api("delete", f"/backups/{slug}"))


# ------------------------------------------------------------ host / sup info
@mcp.tool()
async def supervisor_info() -> str:
    """Get Supervisor info (version, add-ons summary, diagnostics)."""
    return _dump(await _supervisor_api("get", "/supervisor/info"))


@mcp.tool()
async def host_info() -> str:
    """Get host info (OS, disk usage, hostname) for HA OS / Supervised."""
    return _dump(await _supervisor_api("get", "/host/info"))


@mcp.tool()
async def update_supervisor() -> str:
    """Update the Supervisor itself to the latest version."""
    return _dump(await _supervisor_api("post", "/supervisor/update", {}))


@mcp.tool()
async def reboot_host(confirm: bool = False) -> str:
    """Reboot the host machine (HA OS). Requires confirm=True."""
    if not confirm:
        raise HAError("Refusing to reboot the host without confirm=True.")
    return _dump(await _supervisor_api("post", "/host/reboot", {}))
