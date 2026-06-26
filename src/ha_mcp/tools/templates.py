"""Templates and historical/diagnostic data."""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp


@mcp.tool()
async def render_template(template: str) -> str:
    """Render a Jinja2 template against live Home Assistant state.

    Example: "{{ states('sensor.temperature') }}" or
    "{{ states.light | selectattr('state','eq','on') | list | count }}".
    """
    return _dump(await client.rest_post("/template", {"template": template}))


@mcp.tool()
async def get_history(entity_id: str, start_time: str | None = None,
                      end_time: str | None = None, minimal: bool = True) -> str:
    """Get state history for an entity.

    Args:
        entity_id: Entity to fetch history for.
        start_time: Optional ISO 8601 start timestamp; defaults to ~1 day ago.
        end_time: Optional ISO 8601 end timestamp.
        minimal: If true, return only state + timestamp (smaller responses).
    """
    path = "/history/period"
    if start_time:
        path += f"/{start_time}"
    params: dict[str, Any] = {"filter_entity_id": entity_id}
    if end_time:
        params["end_time"] = end_time
    if minimal:
        params["minimal_response"] = ""
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


@mcp.tool()
async def get_statistics(statistic_id: str, period: str = "hour",
                         start_time: str | None = None, end_time: str | None = None) -> str:
    """Get long-term statistics for a statistic id (e.g. an energy sensor).

    Args:
        statistic_id: e.g. "sensor.energy_total".
        period: "5minute", "hour", "day", "week" or "month".
    """
    cmd: dict[str, Any] = {
        "type": "recorder/statistics_during_period",
        "statistic_ids": [statistic_id],
        "period": period,
    }
    if start_time:
        cmd["start_time"] = start_time
    if end_time:
        cmd["end_time"] = end_time
    return _dump(await client.ws_command(cmd))
