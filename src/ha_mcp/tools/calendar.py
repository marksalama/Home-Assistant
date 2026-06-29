"""Calendar: list calendars, get events (REST), manage events (WS).

Calendars are entities (``calendar.*``) listed via ``/states``. Events are
fetched via ``GET /api/calendars/{entity_id}`` and managed via the
``calendar/event/*`` WebSocket commands.
"""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp
from ..ha_client import HAError


@mcp.tool()
async def list_calendars() -> str:
    """List all calendar entities (``calendar.*`` domain)."""
    states = await client.rest_get("/states")
    cals = [
        {"entity_id": s["entity_id"], "state": s["state"],
         "friendly_name": s.get("attributes", {}).get("friendly_name", "")}
        for s in states if s["entity_id"].startswith("calendar.")
    ]
    return _dump({"count": len(cals), "calendars": cals})


@mcp.tool()
async def get_calendar_events(
    entity_id: str,
    start: str,
    end: str | None = None,
) -> str:
    """Get events from a calendar in a date range via the REST calendar API.

    Args:
        entity_id: e.g. "calendar.personal".
        start: ISO 8601 start datetime, e.g. "2026-07-01T00:00:00".
        end: Optional ISO 8601 end datetime.
    """
    params: dict[str, Any] = {"start": start}
    if end:
        params["end"] = end
    return _dump(await client.rest_get(f"/calendars/{entity_id}", params=params))


@mcp.tool()
async def create_calendar_event(
    entity_id: str,
    summary: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
    rrule: str | None = None,
) -> str:
    """Create a calendar event via the ``calendar/event/create`` WS command.

    Args:
        entity_id: e.g. "calendar.personal".
        summary: Event title.
        start: ISO 8601 start datetime.
        end: ISO 8601 end datetime.
        description: Optional longer text.
        location: Optional location string.
        rrule: Optional recurrence rule (RFC 5545).
    """
    event: dict[str, Any] = {"summary": summary, "start": start, "end": end}
    if description:
        event["description"] = description
    if location:
        event["location"] = location
    if rrule:
        event["rrule"] = rrule
    return _dump(await client.ws_command({
        "type": "calendar/event/create",
        "entity_id": entity_id,
        "event": event,
    }))


@mcp.tool()
async def update_calendar_event(
    entity_id: str,
    uid: str,
    summary: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    location: str | None = None,
    rrule: str | None = None,
) -> str:
    """Update a calendar event via the ``calendar/event/update`` WS command.
    Provide the uid (from get_calendar_events) and only the fields to change."""
    event: dict[str, Any] = {}
    if summary is not None:
        event["summary"] = summary
    if start is not None:
        event["start"] = start
    if end is not None:
        event["end"] = end
    if description is not None:
        event["description"] = description
    if location is not None:
        event["location"] = location
    if rrule is not None:
        event["rrule"] = rrule
    if not event:
        raise HAError("At least one field to update is required.")
    return _dump(await client.ws_command({
        "type": "calendar/event/update",
        "entity_id": entity_id,
        "uid": uid,
        "event": event,
    }))


@mcp.tool()
async def remove_calendar_event(
    entity_id: str,
    uid: str,
    confirm: bool = False,
) -> str:
    """Remove a calendar event via the ``calendar/event/delete`` WS command.
    Requires confirm=True."""
    if not confirm:
        raise HAError("Refusing to remove a calendar event without confirm=True.")
    return _dump(await client.ws_command({
        "type": "calendar/event/delete",
        "entity_id": entity_id,
        "uid": uid,
    }))
