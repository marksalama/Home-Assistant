"""States & control: read states, call services, set states, fire events."""

from __future__ import annotations

import asyncio
from typing import Any

from ..app import _collect_overview, _dump, _parse_fields, client, mcp
from ..ha_client import HAError


@mcp.tool()
async def list_entities(domain: str | None = None, search: str | None = None,
                        fields: str | None = None, state: str | None = None,
                        limit: int = 0, offset: int = 0) -> str:
    """List entities with their current state.

    Args:
        domain: Optional domain filter, e.g. "light", "switch", "sensor".
        search: Optional case-insensitive substring matched against entity_id
            and friendly name.
        fields: Comma-separated field names to include per entity (e.g.
            "entity_id,state"). Saves tokens on large results.
        state: Optional exact state filter, e.g. "on" or "unavailable".
        limit: Maximum number of entities to return (0 = all). Use together
            with offset to paginate very large installations.
        offset: Skip this many matches before returning results.
    """
    field_set = _parse_fields(fields)
    states = await client.rest_get("/states")
    result = []
    for s in states:
        eid = s["entity_id"]
        if domain and not eid.startswith(domain + "."):
            continue
        name = s.get("attributes", {}).get("friendly_name", "")
        if search and search.lower() not in eid.lower() and search.lower() not in name.lower():
            continue
        if state is not None and s["state"] != state:
            continue
        entry = {"entity_id": eid, "state": s["state"], "friendly_name": name}
        if field_set:
            entry = {k: v for k, v in entry.items() if k in field_set}
        result.append(entry)
    total = len(result)
    if offset > 0:
        result = result[offset:]
    if limit > 0:
        result = result[:limit]
    return _dump({"count": total, "returned": len(result), "offset": offset,
                  "entities": result})


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
    return _dump(await _collect_overview())


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


# ---------------------------------------------------------------- webhooks
@mcp.tool()
async def trigger_webhook(webhook_id: str, data: dict | None = None) -> str:
    """Trigger a webhook-based automation by POSTing to /api/webhook/<id>.

    Args:
        webhook_id: The webhook id configured in the automation trigger.
        data: Optional JSON payload passed to the automation as trigger data.
    """
    return _dump(await client.rest_post(f"/webhook/{webhook_id}", data or {}))
