"""Technical maintenance & debugging: log levels, database purge, MQTT,
energy preferences and entity diagnostics."""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp
from ..ha_client import HAError


# ------------------------------------------------------------- logging levels
@mcp.tool()
async def set_log_level(integration: str, level: str) -> str:
    """Raise/lower logging for one integration to help debugging.

    Args:
        integration: e.g. "homeassistant.components.mqtt" or "zha".
        level: debug, info, warning, error or critical.
    """
    return _dump(await client.rest_post(
        "/services/logger/set_level", {integration: level}))


@mcp.tool()
async def set_default_log_level(level: str) -> str:
    """Set the global default log level (debug/info/warning/error/critical)."""
    return _dump(await client.rest_post(
        "/services/logger/set_default_level", {"level": level}))


# ------------------------------------------------------------------ recorder
@mcp.tool()
async def purge_database(keep_days: int = 10, repack: bool = False,
                         apply_filter: bool = False) -> str:
    """Purge old history from the recorder database to optimize size/performance.

    Args:
        keep_days: How many days of history to keep.
        repack: Rewrite the database to reclaim disk space (slower).
        apply_filter: Apply the recorder include/exclude filters during purge.
    """
    return _dump(await client.rest_post(
        "/services/recorder/purge",
        {"keep_days": keep_days, "repack": repack, "apply_filter": apply_filter}))


# ---------------------------------------------------------------------- mqtt
@mcp.tool()
async def mqtt_publish(topic: str, payload: str, retain: bool = False, qos: int = 0) -> str:
    """Publish a message to an MQTT topic (requires the MQTT integration)."""
    return _dump(await client.rest_post(
        "/services/mqtt/publish",
        {"topic": topic, "payload": payload, "retain": retain, "qos": qos}))


# -------------------------------------------------------------------- energy
@mcp.tool()
async def get_energy_prefs() -> str:
    """Get the Energy dashboard configuration (sources, devices)."""
    return _dump(await client.ws_command({"type": "energy/get_prefs"}))


@mcp.tool()
async def save_energy_prefs(prefs: dict) -> str:
    """Overwrite the Energy dashboard configuration. `prefs` matches the
    structure returned by get_energy_prefs (energy_sources, device_consumption)."""
    return _dump(await client.ws_command({"type": "energy/save_prefs", **prefs}))


# ------------------------------------------------------------ entity diagnose
@mcp.tool()
async def diagnose_entity(entity_id: str) -> str:
    """Gather everything about one entity in a single view for debugging:
    its live state, registry entry, owning device and config entry."""
    out: dict[str, Any] = {"entity_id": entity_id}
    try:
        out["state"] = await client.rest_get(f"/states/{entity_id}")
    except Exception as exc:  # noqa: BLE001
        out["state_error"] = str(exc)

    entry = None
    try:
        registry = await client.ws_command({"type": "config/entity_registry/list"})
        entry = next((e for e in registry if e.get("entity_id") == entity_id), None)
        out["registry"] = entry
    except Exception as exc:  # noqa: BLE001
        out["registry_error"] = str(exc)

    if entry and entry.get("device_id"):
        try:
            devices = await client.ws_command({"type": "config/device_registry/list"})
            out["device"] = next((d for d in devices if d.get("id") == entry["device_id"]), None)
        except Exception as exc:  # noqa: BLE001
            out["device_error"] = str(exc)

    return _dump(out)


# --------------------------------------------------------- related & repairs
@mcp.tool()
async def search_related(item_type: str, item_id: str) -> str:
    """Find everything related to an entity, device, area, config entry,
    automation, scene, script or group — in one call.

    Great for questions like "what depends on this device?" or "which
    automations use this entity?".

    Args:
        item_type: One of entity, device, area, config_entry, automation,
            scene, script, group.
        item_id: The id of that item (e.g. "light.kitchen", a device id,
            an area id, or an automation entity_id).
    """
    allowed = {"entity", "device", "area", "config_entry", "automation",
               "scene", "script", "group"}
    if item_type not in allowed:
        raise HAError(f"item_type must be one of {sorted(allowed)}, got {item_type!r}")
    return _dump(await client.ws_command({
        "type": "search/related",
        "item_type": item_type,
        "item_id": item_id,
    }))


@mcp.tool()
async def list_repair_issues() -> str:
    """List active repair issues (Settings → Repairs): known problems that
    Home Assistant has detected, with severity and whether they are fixable."""
    result = await client.ws_command({"type": "repairs/list_issues"})
    issues = result.get("issues", result) if isinstance(result, dict) else result
    return _dump({"count": len(issues) if isinstance(issues, list) else None,
                  "issues": issues})


@mcp.tool()
async def recorder_info() -> str:
    """Get recorder (history database) status: whether recording is running,
    migration status and current backlog."""
    return _dump(await client.ws_command({"type": "recorder/info"}))


@mcp.tool()
async def get_config_entry_diagnostics(entry_id: str) -> str:
    """Download the diagnostics dump for an integration (config entry) — the
    same data as the UI's "Download diagnostics" button. Not every integration
    supports this; an HTTP 404 means it doesn't."""
    return _dump(await client.rest_get(f"/diagnostics/config_entry/{entry_id}"))


@mcp.tool()
async def clear_error_log() -> str:
    """Clear all entries from the Home Assistant error log (system_log)."""
    return _dump(await client.rest_post("/services/system_log/clear", {}))
