"""Automation traces: list, inspect and purge traces for debugging.

Uses the ``trace/list`` WS command which requires a ``domain`` parameter
(typically ``"automation"``).
"""

from __future__ import annotations

from ..app import _dump, client, mcp


@mcp.tool()
async def list_automation_traces(
    domain: str = "automation",
    entity_id: str | None = None,
    limit: int = 10,
) -> str:
    """List recent automation/script traces (their last N execution runs).

    Args:
        domain: "automation" (default) or "script".
        entity_id: Optional filter to a single automation (e.g.
            "automation.morning_routine").
        limit: Maximum number of traces to return after filtering (default 10).
    """
    traces = await client.ws_command({"type": "trace/list", "domain": domain})
    if not isinstance(traces, list):
        return _dump({"count": 0, "traces": []})
    if entity_id:
        traces = [t for t in traces if t.get("entity_id") == entity_id]
    traces = traces[:limit]
    return _dump({"count": len(traces), "traces": traces})


@mcp.tool()
async def get_automation_trace(entity_id: str, run_id: str) -> str:
    """Get the full trace detail for one automation run — shows every step,
    condition evaluation and action result.

    Args:
        entity_id: e.g. "automation.morning_routine".
        run_id: The run id from list_automation_traces.
    """
    return _dump(await client.ws_command({
        "type": "trace/get",
        "entity_id": entity_id,
        "run_id": run_id,
    }))


@mcp.tool()
async def delete_automation_trace(entity_id: str, run_id: str) -> str:
    """Delete one automation trace by its run_id."""
    return _dump(await client.ws_command({
        "type": "trace/delete",
        "entity_id": entity_id,
        "run_id": run_id,
    }))
