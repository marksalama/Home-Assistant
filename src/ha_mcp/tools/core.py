"""States & control: read states, call services, set states, fire events."""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp


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

    The `data` dict can target by entity_id, area_id, device_id or label_id, so
    this also covers bulk actions (e.g. all lights in an area).

    Examples:
        call_service("light", "turn_on", {"entity_id": "light.kitchen", "brightness_pct": 60})
        call_service("light", "turn_off", {"area_id": "living_room"})
        call_service("climate", "set_temperature", {"entity_id": "climate.living", "temperature": 21})
    """
    return _dump(await client.rest_post(f"/services/{domain}/{service}", data or {}))


@mcp.tool()
async def fire_event(event_type: str, event_data: dict | None = None) -> str:
    """Fire a custom event on the Home Assistant event bus."""
    return _dump(await client.rest_post(f"/events/{event_type}", event_data or {}))


@mcp.tool()
async def list_services(domain: str | None = None) -> str:
    """List available services, optionally filtered to a single domain."""
    services = await client.rest_get("/services")
    if domain:
        services = [s for s in services if s.get("domain") == domain]
    return _dump(services)
