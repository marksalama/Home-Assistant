"""To-do lists: list, get, add, update and remove items.

Uses the ``todo`` service domain (REST service calls) and ``/states`` for
listing — there is no WebSocket collection API for todos. If the ``todo``
integration is not installed, the listing tools return empty results and the
item tools raise a clear error.
"""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp
from ..ha_client import HAError


@mcp.tool()
async def list_todo_lists() -> str:
    """List all to-do list entities (``todo.*`` domain)."""
    states = await client.rest_get("/states")
    todos = [
        {"entity_id": s["entity_id"], "state": s["state"],
         "friendly_name": s.get("attributes", {}).get("friendly_name", "")}
        for s in states if s["entity_id"].startswith("todo.")
    ]
    return _dump({"count": len(todos), "todo_lists": todos})


@mcp.tool()
async def get_todo_items(
    entity_id: str,
    status: str | None = None,
) -> str:
    """Get all items from a to-do list via the ``todo.get_items`` service.

    Args:
        entity_id: e.g. "todo.shopping_list".
        status: Filter by "needs_action" or "completed". Omit for all.
    """
    data: dict[str, Any] = {"entity_id": entity_id}
    if status:
        data["status"] = status
    return _dump(await client.rest_post("/services/todo/get_items", data, write=False))


@mcp.tool()
async def add_todo_item(
    entity_id: str,
    summary: str,
    due: str | None = None,
    description: str | None = None,
) -> str:
    """Add an item to a to-do list via the ``todo.add_item`` service.

    Args:
        entity_id: e.g. "todo.shopping_list".
        summary: Short text of the item (required).
        due: Optional ISO 8601 due date, e.g. "2026-07-15".
        description: Optional longer description.
    """
    item: dict[str, Any] = {"summary": summary}
    if due:
        item["due"] = due
    if description:
        item["description"] = description
    return _dump(await client.rest_post(
        "/services/todo/add_item", {"entity_id": entity_id, "item": item}))


@mcp.tool()
async def update_todo_item(
    entity_id: str,
    uid: str,
    summary: str | None = None,
    status: str | None = None,
    due: str | None = None,
    description: str | None = None,
) -> str:
    """Update a to-do item via the ``todo.update_item`` service.

    Args:
        uid: The item's unique id (from get_todo_items).
        status: "needs_action" or "completed".
    """
    item: dict[str, Any] = {}
    if summary is not None:
        item["summary"] = summary
    if status is not None:
        item["status"] = status
    if due is not None:
        item["due"] = due
    if description is not None:
        item["description"] = description
    if not item:
        raise HAError("At least one field to update is required.")
    return _dump(await client.rest_post(
        "/services/todo/update_item",
        {"entity_id": entity_id, "uid": uid, "item": item}))


@mcp.tool()
async def remove_todo_item(
    entity_id: str,
    uid: str,
    confirm: bool = False,
) -> str:
    """Remove a to-do item via the ``todo.remove_item`` service. Requires
    confirm=True."""
    if not confirm:
        raise HAError("Refusing to remove a to-do item without confirm=True.")
    return _dump(await client.rest_post(
        "/services/todo/remove_item", {"entity_id": entity_id, "uid": uid}))
