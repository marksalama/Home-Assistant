"""Templates and historical/diagnostic data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..app import _dump, client, mcp
from ..ha_client import HAError


@mcp.tool()
async def render_template(template: str) -> str:
    """Render a Jinja2 template against live Home Assistant state.

    Example: "{{ states('sensor.temperature') }}" or
    "{{ states.light | selectattr('state','eq','on') | list | count }}".
    """
    return _dump(await client.rest_post("/template", {"template": template}, write=False))


@mcp.tool()
async def get_history(entity_id: str, start_time: str | None = None,
                      end_time: str | None = None, minimal: bool = True) -> str:
    """Get state history for one or more entities.

    Args:
        entity_id: Entity to fetch history for. Multiple entities can be
            passed comma-separated, e.g. "sensor.temp1,sensor.temp2".
        start_time: Optional ISO 8601 start timestamp; defaults to ~1 day ago.
        end_time: Optional ISO 8601 end timestamp.
        minimal: If true, return only state + timestamp (smaller responses).
    """
    path = "/history/period"
    if start_time:
        path += f"/{start_time}"
    params: dict[str, Any] = {"filter_entity_id": entity_id.replace(" ", "")}
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
async def get_error_log(level: str | None = None, search: str | None = None,
                        limit: int = 50) -> str:
    """Return recent Home Assistant error log entries via the
    ``system_log/list`` WebSocket command. Each entry includes name, message,
    level, source, timestamp, exception, count and first_occurred.

    Args:
        level: Optional filter: "warning", "error" or "critical".
        search: Optional case-insensitive substring matched against name,
            message and source.
        limit: Maximum entries to return (newest first, default 50).
    """
    entries = await client.ws_command({"type": "system_log/list"})
    if not isinstance(entries, list):
        return _dump(entries)
    if level:
        wanted = level.strip().upper()
        entries = [e for e in entries if str(e.get("level", "")).upper() == wanted]
    if search:
        needle = search.lower()
        entries = [
            e for e in entries
            if needle in " ".join(
                str(x) for x in (e.get("name"), e.get("message"), e.get("source"))
            ).lower()
        ]
    limit = max(1, limit)
    return _dump({"count": len(entries), "entries": entries[:limit]})


@mcp.tool()
async def get_statistics(statistic_id: str, period: str = "hour",
                         start_time: str | None = None, end_time: str | None = None) -> str:
    """Get long-term statistics for one or more statistic ids (e.g. energy
    sensors).

    Args:
        statistic_id: e.g. "sensor.energy_total"; comma-separate for multiple.
        period: "5minute", "hour", "day", "week" or "month".
        start_time: ISO 8601 start; defaults to 24 hours ago (required by HA).
        end_time: Optional ISO 8601 end.
    """
    allowed_periods = {"5minute", "hour", "day", "week", "month"}
    if period not in allowed_periods:
        raise HAError(f"period must be one of {sorted(allowed_periods)}, got {period!r}")
    if not start_time:
        start_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    cmd: dict[str, Any] = {
        "type": "recorder/statistics_during_period",
        "statistic_ids": [s.strip() for s in statistic_id.split(",") if s.strip()],
        "period": period,
        "start_time": start_time,
    }
    if end_time:
        cmd["end_time"] = end_time
    return _dump(await client.ws_command(cmd))


@mcp.tool()
async def list_statistic_ids(search: str | None = None, limit: int = 100) -> str:
    """List the statistic ids known to the recorder (for get_statistics).

    Args:
        search: Optional case-insensitive substring on the statistic id or name.
        limit: Maximum entries to return (default 100).
    """
    ids = await client.ws_command({"type": "recorder/list_statistic_ids"})
    if not isinstance(ids, list):
        return _dump(ids)
    if search:
        needle = search.lower()
        ids = [
            i for i in ids
            if needle in str(i.get("statistic_id", "")).lower()
            or needle in str(i.get("name") or "").lower()
        ]
    limit = max(1, limit)
    return _dump({"count": len(ids), "statistic_ids": ids[:limit]})
