"""MCP server exposing broad control over a Home Assistant installation.

Tools are grouped into:
  * States & control  - read entity states, call services, set states, events
  * Discovery         - services, areas, devices, entity/label registries
  * Helpers           - input_* / counter / timer / schedule helper entities
  * Automations       - read/write/trigger automations via the config API
  * Templates & data  - render Jinja templates, history, logbook, error log
  * System            - core config, config check, restart, reload services
  * Files             - read/write/list raw YAML config files (optional backend)
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_settings
from .files import FilesDisabledError, get_backend
from .ha_client import HAClient, HAError

settings = load_settings()
client = HAClient(settings)
mcp = FastMCP("home-assistant")


def _dump(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _files():
    backend = get_backend(settings)
    if backend is None:
        raise FilesDisabledError(
            "Raw file access is disabled. Set HA_FILES_BACKEND to 'local' or 'ssh' "
            "(see .env.example) to read/write configuration files."
        )
    return backend


# =====================================================================
# States & control
# =====================================================================
@mcp.tool()
async def list_entities(domain: str | None = None, search: str | None = None) -> str:
    """List entities with their current state.

    Args:
        domain: Optional domain filter, e.g. "light", "switch", "sensor".
        search: Optional case-insensitive substring matched against entity_id
            and friendly name.
    """
    states = await client.rest_get("/states")
    result = []
    for s in states:
        eid = s["entity_id"]
        if domain and not eid.startswith(domain + "."):
            continue
        name = s.get("attributes", {}).get("friendly_name", "")
        if search and search.lower() not in eid.lower() and search.lower() not in name.lower():
            continue
        result.append({"entity_id": eid, "state": s["state"], "friendly_name": name})
    return _dump({"count": len(result), "entities": result})


@mcp.tool()
async def get_state(entity_id: str) -> str:
    """Get the full state object (state + all attributes) for one entity."""
    return _dump(await client.rest_get(f"/states/{entity_id}"))


@mcp.tool()
async def set_state(entity_id: str, state: str, attributes: dict | None = None) -> str:
    """Create or override an entity's state in the state machine.

    Note: this only updates Home Assistant's state machine (useful for template
    or MQTT-style entities); it does not command a physical device. Use
    call_service for that.
    """
    body: dict[str, Any] = {"state": state}
    if attributes:
        body["attributes"] = attributes
    return _dump(await client.rest_post(f"/states/{entity_id}", body))


@mcp.tool()
async def call_service(domain: str, service: str, data: dict | None = None) -> str:
    """Call any Home Assistant service (the main way to control devices).

    Examples:
        call_service("light", "turn_on", {"entity_id": "light.kitchen", "brightness_pct": 60})
        call_service("climate", "set_temperature", {"entity_id": "climate.living", "temperature": 21})
        call_service("homeassistant", "toggle", {"entity_id": "switch.fan"})

    Args:
        domain: Service domain, e.g. "light", "switch", "climate", "homeassistant".
        service: Service name, e.g. "turn_on", "turn_off", "toggle".
        data: Service data / target, e.g. {"entity_id": "...", "area_id": "..."}.
    """
    return _dump(await client.rest_post(f"/services/{domain}/{service}", data or {}))


@mcp.tool()
async def fire_event(event_type: str, event_data: dict | None = None) -> str:
    """Fire a custom event on the Home Assistant event bus."""
    return _dump(await client.rest_post(f"/events/{event_type}", event_data or {}))


# =====================================================================
# Discovery
# =====================================================================
@mcp.tool()
async def list_services(domain: str | None = None) -> str:
    """List available services, optionally filtered to a single domain."""
    services = await client.rest_get("/services")
    if domain:
        services = [s for s in services if s.get("domain") == domain]
    return _dump(services)


@mcp.tool()
async def list_areas() -> str:
    """List all areas (rooms/zones) from the area registry."""
    return _dump(await client.ws_command({"type": "config/area_registry/list"}))


@mcp.tool()
async def create_area(name: str) -> str:
    """Create a new area."""
    return _dump(await client.ws_command({"type": "config/area_registry/create", "name": name}))


@mcp.tool()
async def update_area(area_id: str, name: str | None = None, floor_id: str | None = None) -> str:
    """Update an existing area (rename or assign to a floor)."""
    cmd: dict[str, Any] = {"type": "config/area_registry/update", "area_id": area_id}
    if name is not None:
        cmd["name"] = name
    if floor_id is not None:
        cmd["floor_id"] = floor_id
    return _dump(await client.ws_command(cmd))


@mcp.tool()
async def delete_area(area_id: str) -> str:
    """Delete an area."""
    return _dump(await client.ws_command({"type": "config/area_registry/delete", "area_id": area_id}))


@mcp.tool()
async def list_devices() -> str:
    """List all devices from the device registry."""
    return _dump(await client.ws_command({"type": "config/device_registry/list"}))


@mcp.tool()
async def list_entity_registry(domain: str | None = None, search: str | None = None) -> str:
    """List registry entries for entities (ids, names, area, device, disabled state)."""
    entries = await client.ws_command({"type": "config/entity_registry/list"})
    if domain or search:
        filtered = []
        for e in entries:
            eid = e.get("entity_id", "")
            if domain and not eid.startswith(domain + "."):
                continue
            if search and search.lower() not in eid.lower() and search.lower() not in (e.get("name") or e.get("original_name") or "").lower():
                continue
            filtered.append(e)
        entries = filtered
    return _dump(entries)


@mcp.tool()
async def update_entity(
    entity_id: str,
    name: str | None = None,
    new_entity_id: str | None = None,
    area_id: str | None = None,
    icon: str | None = None,
    disabled: bool | None = None,
) -> str:
    """Update an entity registry entry (rename, move to area, change id, enable/disable)."""
    cmd: dict[str, Any] = {"type": "config/entity_registry/update", "entity_id": entity_id}
    if name is not None:
        cmd["name"] = name
    if new_entity_id is not None:
        cmd["new_entity_id"] = new_entity_id
    if area_id is not None:
        cmd["area_id"] = area_id
    if icon is not None:
        cmd["icon"] = icon
    if disabled is not None:
        cmd["disabled_by"] = "user" if disabled else None
    return _dump(await client.ws_command(cmd))


@mcp.tool()
async def list_labels() -> str:
    """List all labels from the label registry."""
    return _dump(await client.ws_command({"type": "config/label_registry/list"}))


@mcp.tool()
async def list_config_entries() -> str:
    """List configured integrations (config entries)."""
    return _dump(await client.ws_command({"type": "config_entries/get"}))


# =====================================================================
# Helpers (input_* / counter / timer / schedule storage collections)
# =====================================================================
_HELPER_DOMAINS = {
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


@mcp.tool()
async def list_helpers(helper_domain: str) -> str:
    """List helper entities of a given domain.

    Args:
        helper_domain: One of input_boolean, input_button, input_number,
            input_text, input_select, input_datetime, counter, timer, schedule.
    """
    if helper_domain not in _HELPER_DOMAINS:
        raise HAError(f"Unsupported helper domain {helper_domain!r}. Allowed: {sorted(_HELPER_DOMAINS)}")
    return _dump(await client.ws_command({"type": f"{helper_domain}/list"}))


@mcp.tool()
async def create_helper(helper_domain: str, config: dict) -> str:
    """Create a helper. `config` must include at least a "name", plus domain-specific
    fields (e.g. input_number needs min/max/step).
    """
    if helper_domain not in _HELPER_DOMAINS:
        raise HAError(f"Unsupported helper domain {helper_domain!r}. Allowed: {sorted(_HELPER_DOMAINS)}")
    return _dump(await client.ws_command({"type": f"{helper_domain}/create", **config}))


@mcp.tool()
async def update_helper(helper_domain: str, helper_id: str, config: dict) -> str:
    """Update a helper by its id (the part after the dot, e.g. for
    input_boolean.guest_mode use helper_id="guest_mode")."""
    if helper_domain not in _HELPER_DOMAINS:
        raise HAError(f"Unsupported helper domain {helper_domain!r}. Allowed: {sorted(_HELPER_DOMAINS)}")
    cmd = {"type": f"{helper_domain}/update", f"{helper_domain}_id": helper_id, **config}
    return _dump(await client.ws_command(cmd))


@mcp.tool()
async def delete_helper(helper_domain: str, helper_id: str) -> str:
    """Delete a helper by its id."""
    if helper_domain not in _HELPER_DOMAINS:
        raise HAError(f"Unsupported helper domain {helper_domain!r}. Allowed: {sorted(_HELPER_DOMAINS)}")
    cmd = {"type": f"{helper_domain}/delete", f"{helper_domain}_id": helper_id}
    return _dump(await client.ws_command(cmd))


# =====================================================================
# Automations (config API, for UI-stored automations.yaml entries)
# =====================================================================
@mcp.tool()
async def get_automation(automation_id: str) -> str:
    """Get an automation's config by its numeric id (the `id:` field)."""
    return _dump(await client.rest_get(f"/config/automation/config/{automation_id}"))


@mcp.tool()
async def upsert_automation(automation_id: str, config: dict) -> str:
    """Create or update an automation by id. `config` is the automation body
    (alias, trigger, condition, action, mode, ...). Reloads automations on save.
    """
    result = await client.rest_post(f"/config/automation/config/{automation_id}", config)
    await client.rest_post("/services/automation/reload", {})
    return _dump(result)


@mcp.tool()
async def delete_automation(automation_id: str) -> str:
    """Delete an automation by id and reload automations."""
    result = await client.rest_delete(f"/config/automation/config/{automation_id}")
    await client.rest_post("/services/automation/reload", {})
    return _dump(result)


@mcp.tool()
async def trigger_automation(entity_id: str) -> str:
    """Manually run an automation now (skips its conditions)."""
    return _dump(await client.rest_post("/services/automation/trigger", {"entity_id": entity_id}))


# =====================================================================
# Templates & historical data
# =====================================================================
@mcp.tool()
async def render_template(template: str) -> str:
    """Render a Jinja2 template against live Home Assistant state.

    Example: "{{ states('sensor.temperature') }}" or
    "{{ states.light | selectattr('state','eq','on') | list | count }}".
    """
    return _dump(await client.rest_post("/template", {"template": template}))


@mcp.tool()
async def get_history(entity_id: str, start_time: str | None = None, end_time: str | None = None) -> str:
    """Get state history for an entity.

    Args:
        entity_id: Entity to fetch history for.
        start_time: Optional ISO 8601 start timestamp; defaults to ~1 day ago.
        end_time: Optional ISO 8601 end timestamp.
    """
    path = "/history/period"
    if start_time:
        path += f"/{start_time}"
    params: dict[str, Any] = {"filter_entity_id": entity_id}
    if end_time:
        params["end_time"] = end_time
    return _dump(await client.rest_get(path, params=params))


@mcp.tool()
async def get_logbook(entity_id: str | None = None, start_time: str | None = None) -> str:
    """Get logbook entries, optionally filtered by entity and start time."""
    path = "/logbook"
    if start_time:
        path += f"/{start_time}"
    params = {"entity": entity_id} if entity_id else None
    return _dump(await client.rest_get(path, params=params))


@mcp.tool()
async def get_error_log() -> str:
    """Return the Home Assistant error log (home-assistant.log)."""
    return _dump(await client.rest_get("/error_log"))


# =====================================================================
# System
# =====================================================================
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


# =====================================================================
# Files (raw YAML access - optional backend)
# =====================================================================
@mcp.tool()
async def list_config_files(path: str = "") -> str:
    """List files/folders in the HA config directory (relative path, "" = root).

    Requires HA_FILES_BACKEND=local or ssh.
    """
    backend = _files()
    entries = await asyncio.to_thread(backend.list_dir, path)
    return _dump([asdict(e) for e in entries])


@mcp.tool()
async def read_config_file(path: str) -> str:
    """Read a text/YAML file from the HA config directory.

    Requires HA_FILES_BACKEND=local or ssh.
    """
    backend = _files()
    return await asyncio.to_thread(backend.read, path)


@mcp.tool()
async def write_config_file(path: str, content: str) -> str:
    """Write (create/overwrite) a text/YAML file in the HA config directory.

    After editing core YAML, call check_config() before restart_home_assistant().
    Requires HA_FILES_BACKEND=local or ssh.
    """
    backend = _files()
    await asyncio.to_thread(backend.write, path, content)
    return _dump({"ok": True, "path": path, "bytes": len(content.encode("utf-8"))})


@mcp.tool()
async def delete_config_file(path: str, confirm: bool = False) -> str:
    """Delete a file from the HA config directory. Requires confirm=True.

    Requires HA_FILES_BACKEND=local or ssh.
    """
    if not confirm:
        raise HAError("Refusing to delete without confirm=True.")
    backend = _files()
    await asyncio.to_thread(backend.delete, path)
    return _dump({"ok": True, "deleted": path})
