"""Entity groups: list, create, update and remove groups.

Uses the ``group.set`` and ``group.remove`` REST service calls — there is no
WebSocket collection API for groups. Groups are listed via ``/states`` filtered
by the ``group.*`` domain.
"""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp
from ..ha_client import HAError


@mcp.tool()
async def list_groups() -> str:
    """List all group entities (``group.*`` domain)."""
    states = await client.rest_get("/states")
    groups = [
        {"entity_id": s["entity_id"], "state": s["state"],
         "friendly_name": s.get("attributes", {}).get("friendly_name", ""),
         "entities": s.get("attributes", {}).get("entity_id", [])}
        for s in states if s["entity_id"].startswith("group.")
    ]
    return _dump({"count": len(groups), "groups": groups})


@mcp.tool()
async def create_group(
    name: str,
    entities: list[str],
    icon: str | None = None,
    all: bool = False,
) -> str:
    """Create a group of entities via the ``group.set`` service.

    Args:
        name: Display name for the group.
        entities: List of entity_ids to include.
        icon: Optional MDI icon, e.g. "mdi:lightbulb-group".
        all: If true, the group state is 'on' only when ALL entities are on
            (otherwise: any one is on = on).
    """
    data: dict[str, Any] = {"name": name, "entities": entities, "all": all}
    if icon:
        data["icon"] = icon
    return _dump(await client.rest_post("/services/group/set", data))


@mcp.tool()
async def update_group(
    object_id: str,
    name: str | None = None,
    entities: list[str] | None = None,
    icon: str | None = None,
    all: bool | None = None,
    add_entities: list[str] | None = None,
    remove_entities: list[str] | None = None,
) -> str:
    """Update a group via the ``group.set`` service.

    Args:
        object_id: The group's object_id (e.g. "my_group" for group.my_group).
        entities: Replace the full entity list.
        add_entities: Add these entities to the existing group.
        remove_entities: Remove these entities from the existing group.
    """
    data: dict[str, Any] = {"object_id": object_id}
    if name is not None:
        data["name"] = name
    if entities is not None:
        data["entities"] = entities
    if icon is not None:
        data["icon"] = icon
    if all is not None:
        data["all"] = all
    if add_entities is not None:
        data["add_entities"] = add_entities
    if remove_entities is not None:
        data["remove_entities"] = remove_entities
    return _dump(await client.rest_post("/services/group/set", data))


@mcp.tool()
async def remove_group(
    object_id: str,
    confirm: bool = False,
) -> str:
    """Remove a group via the ``group.remove`` service. Requires confirm=True.

    Args:
        object_id: The group's object_id (e.g. "my_group" for group.my_group).
    """
    if not confirm:
        raise HAError("Refusing to remove a group without confirm=True.")
    return _dump(await client.rest_post(
        "/services/group/remove", {"object_id": object_id}))
