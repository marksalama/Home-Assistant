"""System: core config, config check, restart, reload, notifications,
updates and system health."""

from __future__ import annotations

from ..app import _dump, client, mcp
from ..ha_client import HAError


@mcp.tool()
async def get_config() -> str:
    """Get core configuration (version, location, unit system, components, ...)."""
    return _dump(await client.rest_get("/config"))


@mcp.tool()
async def check_config() -> str:
    """Validate the configuration without restarting. Run this before restarting
    after editing YAML files."""
    return _dump(await client.rest_post("/config/core/check_config", {}))


@mcp.tool()
async def restart_home_assistant(confirm: bool = False) -> str:
    """Restart Home Assistant core. Requires confirm=True. Run check_config first."""
    if not confirm:
        raise HAError("Refusing to restart without confirm=True. Run check_config() first.")
    return _dump(await client.rest_post("/services/homeassistant/restart", {}))


@mcp.tool()
async def reload_domain(domain: str) -> str:
    """Reload a domain's YAML config without a full restart (calls <domain>.reload).

    Common values: "automation", "script", "scene", "template", "input_boolean",
    "rest", "command_line", "group", "homeassistant" (reload core config).
    """
    service = "reload_core_config" if domain == "homeassistant" else "reload"
    return _dump(await client.rest_post(f"/services/{domain}/{service}", {}))


@mcp.tool()
async def system_health() -> str:
    """Return Home Assistant system health information (integrations status)."""
    return _dump(await client.ws_command({"type": "system_health/info"}))


# ------------------------------------------------------------- notifications
@mcp.tool()
async def list_notifications() -> str:
    """List active persistent notifications."""
    return _dump(await client.ws_command({"type": "persistent_notification/get"}))


@mcp.tool()
async def create_notification(message: str, title: str | None = None,
                              notification_id: str | None = None) -> str:
    """Create a persistent notification shown in the HA UI."""
    data: dict = {"message": message}
    if title:
        data["title"] = title
    if notification_id:
        data["notification_id"] = notification_id
    return _dump(await client.rest_post("/services/persistent_notification/create", data))


@mcp.tool()
async def dismiss_notification(notification_id: str) -> str:
    """Dismiss a persistent notification by its id."""
    return _dump(await client.rest_post(
        "/services/persistent_notification/dismiss", {"notification_id": notification_id}))


@mcp.tool()
async def notify(message: str, title: str | None = None, target: str = "notify") -> str:
    """Send a notification via a notify service (e.g. mobile app).

    Args:
        target: The notify service name without the 'notify.' prefix, e.g.
            "mobile_app_phone" or "notify" for the default.
    """
    data: dict = {"message": message}
    if title:
        data["title"] = title
    return _dump(await client.rest_post(f"/services/notify/{target}", data))


# -------------------------------------------------------------------- updates
@mcp.tool()
async def list_updates() -> str:
    """List entities that have an update available (integrations, add-ons, HA)."""
    states = await client.rest_get("/states")
    items = [
        {
            "entity_id": s["entity_id"],
            "title": s.get("attributes", {}).get("title")
            or s.get("attributes", {}).get("friendly_name", ""),
            "installed_version": s.get("attributes", {}).get("installed_version"),
            "latest_version": s.get("attributes", {}).get("latest_version"),
        }
        for s in states
        if s["entity_id"].startswith("update.") and s["state"] == "on"
    ]
    return _dump({"count": len(items), "updates": items})


@mcp.tool()
async def install_update(entity_id: str, confirm: bool = False) -> str:
    """Install a pending update for an update entity. Requires confirm=True."""
    if not confirm:
        raise HAError("Refusing to install an update without confirm=True.")
    return _dump(await client.rest_post("/services/update/install", {"entity_id": entity_id}))
