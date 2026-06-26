"""Technical maintenance & debugging: log levels, database purge, MQTT,
energy preferences and entity diagnostics."""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp


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
