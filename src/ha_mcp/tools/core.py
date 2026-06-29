"""States & control: read states, call services, set states, fire events."""

from __future__ import annotations

import asyncio
from typing import Any

from ..app import _dump, client, mcp
from ..ha_client import HAError


@mcp.tool()
async def list_entities(domain: str | None = None, search: str | None = None,
                        fields: str | None = None) -> str:
    """List entities with their current state.

    Args:
        domain: Optional domain filter, e.g. "light", "switch", "sensor".
        search: Optional case-insensitive substring matched against entity_id
            and friendly name.
        fields: Comma-separated field names to include per entity (e.g.
            "entity_id,state"). Saves tokens on large results.
    """
    field_set = {f.strip() for f in fields.split(",")} if fields else None
    states = await client.rest_get("/states")
    result = []
    for s in states:
        eid = s["entity_id"]
        if domain and not eid.startswith(domain + "."):
            continue
        name = s.get("attributes", {}).get("friendly_name", "")
        if search and search.lower() not in eid.lower() and search.lower() not in name.lower():
            continue
        entry = {"entity_id": eid, "state": s["state"], "friendly_name": name}
        if field_set:
            entry = {k: v for k, v in entry.items() if k in field_set}
        result.append(entry)
    return _dump({"count": len(result), "entities": result})


@mcp.tool()
async def get_state(entity_id: str, attribute_keys: str | None = None) -> str:
    """Get the full state object (state + all attributes) for one entity.

    Args:
        attribute_keys: Comma-separated attribute keys to include (e.g.
            "brightness,color_temp"). Saves tokens on entities with large
            attribute sets. Omit for all attributes.
    """
    state = await client.rest_get(f"/states/{entity_id}")
    if attribute_keys is not None:
        keys = {k.strip() for k in attribute_keys.split(",")}
        if "attributes" in state and isinstance(state["attributes"], dict):
            state["attributes"] = {
                k: v for k, v in state["attributes"].items() if k in keys
            }
    return _dump(state)


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


# ---------------------------------------------------------------- system overview
@mcp.tool()
async def get_overview() -> str:
    """Return a structured summary of the entire Home Assistant installation:
    version, entity counts per domain, automation/script/scene counts, areas &
    floors, pending updates, config entries, and recent errors."""
    config, states, config_entries = await asyncio.gather(
        client.rest_get("/config"),
        client.rest_get("/states"),
        client.ws_command({"type": "config_entries/get"}),
    )

    entities_by_domain: dict[str, int] = {}
    automation_count = 0
    automation_enabled = 0
    script_count = 0
    scene_count = 0
    update_pending = 0
    update_entities: list[dict[str, Any]] = []
    for s in states:
        eid: str = s["entity_id"]
        domain = eid.partition(".")[0]
        entities_by_domain[domain] = entities_by_domain.get(domain, 0) + 1
        if domain == "automation":
            automation_count += 1
            if s.get("state") == "on":
                automation_enabled += 1
        elif domain == "script":
            script_count += 1
        elif domain == "scene":
            scene_count += 1
        elif domain == "update":
            if s.get("state") == "on":
                attrs = s.get("attributes", {})
                update_entities.append({
                    "entity_id": eid,
                    "title": attrs.get("title") or attrs.get("friendly_name", ""),
                    "installed_version": attrs.get("installed_version"),
                    "latest_version": attrs.get("latest_version"),
                })
                update_pending += 1

    # count error log errors
    error_count = 0
    try:
        errors = await client.ws_command({"type": "system_log/list"})
        error_count = len(errors) if isinstance(errors, list) else 0
    except Exception:
        pass

    # areas & floors (fire-and-forget – graceful if WS fails)
    areas: list[dict[str, Any]] = []
    floors: list[dict[str, Any]] = []
    try:
        areas = await client.ws_command({"type": "config/area_registry/list"})
    except Exception:
        pass
    try:
        floors = await client.ws_command({"type": "config/floor_registry/list"})
    except Exception:
        pass

    integration_count = len(config_entries) if isinstance(config_entries, list) else 0
    integration_failed = sum(
        1 for e in (config_entries if isinstance(config_entries, list) else [])
        if e.get("state") == "not_loaded"
    )

    return _dump({
        "version": config.get("version") if isinstance(config, dict) else None,
        "location_name": config.get("location_name") if isinstance(config, dict) else None,
        "unit_system": config.get("unit_system", {}).get("temperature") if isinstance(config, dict) else None,
        "entities_by_domain": dict(sorted(entities_by_domain.items())),
        "automation_count": automation_count,
        "automation_enabled": automation_enabled,
        "script_count": script_count,
        "scene_count": scene_count,
        "pending_updates": update_pending,
        "update_entities": update_entities,
        "errors_last_hour": error_count,
        "integrations": integration_count,
        "integrations_failed": integration_failed,
        "areas": len(areas),
        "floors": len(floors),
    })


# --------------------------------------------------------------- fuzzy search
@mcp.tool()
async def fuzzy_search(
    query: str,
    domains: list[str] | None = None,
    max_results: int = 10,
) -> str:
    """Search entities, areas, labels and devices with a fuzzy query.
    Returns ranked results from entity id, friendly name, area, and label.
    """
    states, entity_registry, areas_out, labels = await asyncio.gather(
        client.rest_get("/states"),
        client.ws_command({"type": "config/entity_registry/list"}),
        client.ws_command({"type": "config/area_registry/list"}),
        client.ws_command({"type": "config/label_registry/list"}),
    )

    # build lookup maps
    entity_map: dict[str, Any] = {}
    for e in (entity_registry if isinstance(entity_registry, list) else []):
        entity_map[e.get("entity_id", "")] = e

    area_names: dict[str, str] = {}
    for a in (areas_out if isinstance(areas_out, list) else []):
        area_names[a.get("area_id", "")] = a.get("name", "")

    label_names: dict[str, str] = {}
    for lb in (labels if isinstance(labels, list) else []):
        label_names[lb.get("label_id", "")] = lb.get("name", "")

    q = query.lower().split()
    results: list[dict[str, Any]] = []

    for s in (states if isinstance(states, list) else []):
        eid: str = s["entity_id"]
        domain = eid.partition(".")[0]
        if domains and domain not in domains:
            continue

        attrs = s.get("attributes", {})
        friendly_name = attrs.get("friendly_name", "") or ""
        area_id = entity_map.get(eid, {}).get("area_id")
        area_name = area_names.get(area_id or "", "") if area_id else attrs.get("friendly_area", "")

        # gather labels for this entity
        entity_labels = []
        for lbl_id in entity_map.get(eid, {}).get("labels", []) or []:
            name = label_names.get(lbl_id)
            if name:
                entity_labels.append(name)

        # simple token-overlap score
        search_text = " ".join(
            x for x in [eid, friendly_name, area_name, *entity_labels] if x
        ).lower()
        score = sum(1 for t in q if t in search_text)

        if score > 0 or query.lower() in eid.lower() or query.lower() in friendly_name.lower():
            results.append({
                "entity_id": eid,
                "state": s["state"],
                "friendly_name": friendly_name,
                "area": area_name or None,
                "labels": entity_labels,
                "score": score,
            })

    results.sort(key=lambda r: (r["score"], r["entity_id"]), reverse=True)

    # Return either total matching or the number of items actually scored > 0
    return _dump({
        "query": query,
        "total_results": len(results),
        "results": results[:max_results],
    })


# ---------------------------------------------------------------- bulk control
@mcp.tool()
async def bulk_control(
    service: str,
    targets: list[dict],
    data: dict | None = None,
) -> str:
    """Call a service for multiple targets in parallel — one call for a whole
    house or area.

    ``service`` is ``"domain.service"`` (e.g. ``"light.turn_off"``).
    ``targets`` is a list each containing entity_id, area_id, device_id or
    label_id.
    ``data`` are optional extra service data applied to every call.

    Returns per-target results so you can see exactly what succeeded.
    """
    domain, _, svc = service.partition(".")
    if not svc:
        raise HAError(f"service must be 'domain.service', got {service!r}")

    async def _one(target: dict) -> dict[str, Any]:
        body: dict[str, Any] = dict(target)
        if data:
            body.update(data)
        try:
            await client.rest_post(f"/services/{domain}/{svc}", body)
            return {"target": target, "ok": True}
        except HAError as exc:
            return {"target": target, "ok": False, "error": str(exc)}

    outcomes = await asyncio.gather(*(_one(t) for t in targets))
    return _dump({
        "service": service,
        "total": len(outcomes),
        "succeeded": sum(1 for o in outcomes if o["ok"]),
        "results": outcomes,
    })
