"""Registries: areas, floors, devices, entities, labels, persons, zones,
config entries (integrations)."""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp

# --------------------------------------------------------------------- areas
@mcp.tool()
async def list_areas() -> str:
    """List all areas (rooms/zones) from the area registry."""
    return _dump(await client.ws_command({"type": "config/area_registry/list"}))


@mcp.tool()
async def create_area(name: str, floor_id: str | None = None) -> str:
    """Create a new area, optionally placing it on a floor."""
    cmd: dict[str, Any] = {"type": "config/area_registry/create", "name": name}
    if floor_id is not None:
        cmd["floor_id"] = floor_id
    return _dump(await client.ws_command(cmd))


@mcp.tool()
async def update_area(area_id: str, name: str | None = None, floor_id: str | None = None,
                      icon: str | None = None) -> str:
    """Update an existing area (rename, assign to a floor, set an icon)."""
    cmd: dict[str, Any] = {"type": "config/area_registry/update", "area_id": area_id}
    if name is not None:
        cmd["name"] = name
    if floor_id is not None:
        cmd["floor_id"] = floor_id
    if icon is not None:
        cmd["icon"] = icon
    return _dump(await client.ws_command(cmd))


@mcp.tool()
async def delete_area(area_id: str) -> str:
    """Delete an area."""
    return _dump(await client.ws_command({"type": "config/area_registry/delete", "area_id": area_id}))


# -------------------------------------------------------------------- floors
@mcp.tool()
async def list_floors() -> str:
    """List all floors from the floor registry."""
    return _dump(await client.ws_command({"type": "config/floor_registry/list"}))


@mcp.tool()
async def create_floor(name: str, level: int | None = None, icon: str | None = None) -> str:
    """Create a new floor (e.g. 'Ground floor', level 0)."""
    cmd: dict[str, Any] = {"type": "config/floor_registry/create", "name": name}
    if level is not None:
        cmd["level"] = level
    if icon is not None:
        cmd["icon"] = icon
    return _dump(await client.ws_command(cmd))


@mcp.tool()
async def update_floor(floor_id: str, name: str | None = None, level: int | None = None,
                       icon: str | None = None) -> str:
    """Update a floor."""
    cmd: dict[str, Any] = {"type": "config/floor_registry/update", "floor_id": floor_id}
    if name is not None:
        cmd["name"] = name
    if level is not None:
        cmd["level"] = level
    if icon is not None:
        cmd["icon"] = icon
    return _dump(await client.ws_command(cmd))


@mcp.tool()
async def delete_floor(floor_id: str) -> str:
    """Delete a floor."""
    return _dump(await client.ws_command({"type": "config/floor_registry/delete", "floor_id": floor_id}))


# ------------------------------------------------------------------- devices
@mcp.tool()
async def list_devices(search: str | None = None) -> str:
    """List devices from the device registry (optionally filtered by name)."""
    devices = await client.ws_command({"type": "config/device_registry/list"})
    if search:
        s = search.lower()
        devices = [d for d in devices if s in (d.get("name_by_user") or d.get("name") or "").lower()]
    return _dump(devices)


@mcp.tool()
async def update_device(device_id: str, name_by_user: str | None = None,
                        area_id: str | None = None, disabled: bool | None = None) -> str:
    """Update a device (rename, assign to area, enable/disable)."""
    cmd: dict[str, Any] = {"type": "config/device_registry/update", "device_id": device_id}
    if name_by_user is not None:
        cmd["name_by_user"] = name_by_user
    if area_id is not None:
        cmd["area_id"] = area_id
    if disabled is not None:
        cmd["disabled_by"] = "user" if disabled else None
    return _dump(await client.ws_command(cmd))


# ------------------------------------------------------------- entity registry
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
            label = (e.get("name") or e.get("original_name") or "").lower()
            if search and search.lower() not in eid.lower() and search.lower() not in label:
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
    labels: list[str] | None = None,
    hidden: bool | None = None,
    disabled: bool | None = None,
) -> str:
    """Update an entity registry entry (rename, move to area, change id, set
    labels, hide, enable/disable)."""
    cmd: dict[str, Any] = {"type": "config/entity_registry/update", "entity_id": entity_id}
    if name is not None:
        cmd["name"] = name
    if new_entity_id is not None:
        cmd["new_entity_id"] = new_entity_id
    if area_id is not None:
        cmd["area_id"] = area_id
    if icon is not None:
        cmd["icon"] = icon
    if labels is not None:
        cmd["labels"] = labels
    if hidden is not None:
        cmd["hidden_by"] = "user" if hidden else None
    if disabled is not None:
        cmd["disabled_by"] = "user" if disabled else None
    return _dump(await client.ws_command(cmd))


# -------------------------------------------------------------------- labels
@mcp.tool()
async def list_labels() -> str:
    """List all labels from the label registry."""
    return _dump(await client.ws_command({"type": "config/label_registry/list"}))


@mcp.tool()
async def create_label(name: str, color: str | None = None, icon: str | None = None) -> str:
    """Create a label (used to group/target entities and devices)."""
    cmd: dict[str, Any] = {"type": "config/label_registry/create", "name": name}
    if color is not None:
        cmd["color"] = color
    if icon is not None:
        cmd["icon"] = icon
    return _dump(await client.ws_command(cmd))


@mcp.tool()
async def delete_label(label_id: str) -> str:
    """Delete a label."""
    return _dump(await client.ws_command({"type": "config/label_registry/delete", "label_id": label_id}))


# ---------------------------------------------------------- persons & zones
@mcp.tool()
async def list_persons() -> str:
    """List configured persons (presence tracking)."""
    return _dump(await client.ws_command({"type": "person/list"}))


@mcp.tool()
async def list_zones() -> str:
    """List zones (geographic areas for presence)."""
    return _dump(await client.ws_command({"type": "zone/list"}))


@mcp.tool()
async def create_zone(config: dict) -> str:
    """Create a zone. `config` needs name, latitude, longitude, radius (and
    optionally icon, passive)."""
    return _dump(await client.ws_command({"type": "zone/create", **config}))


# ----------------------------------------------------------- config entries
@mcp.tool()
async def list_config_entries() -> str:
    """List configured integrations (config entries)."""
    return _dump(await client.ws_command({"type": "config_entries/get"}))


@mcp.tool()
async def reload_config_entry(entry_id: str) -> str:
    """Reload an integration (config entry) by its entry_id."""
    return _dump(await client.rest_post(f"/config/config_entries/entry/{entry_id}/reload", {}))


@mcp.tool()
async def delete_config_entry(entry_id: str, confirm: bool = False) -> str:
    """Remove an integration (config entry). Requires confirm=True."""
    from ..ha_client import HAError

    if not confirm:
        raise HAError("Refusing to delete an integration without confirm=True.")
    return _dump(await client.rest_delete(f"/config/config_entries/entry/{entry_id}"))
