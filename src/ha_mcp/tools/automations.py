"""Automations, scripts and scenes via the Home Assistant config API.

These endpoints back the UI editors and write to automations.yaml / scripts.yaml /
scenes.yaml. After every write we reload the relevant domain so changes take
effect immediately.
"""

from __future__ import annotations

from ..app import _dump, client, mcp


# ---------------------------------------------------------------- automations
@mcp.tool()
async def list_automations() -> str:
    """List all automations with their entity_id, state and friendly name."""
    states = await client.rest_get("/states")
    items = [
        {
            "entity_id": s["entity_id"],
            "state": s["state"],
            "friendly_name": s.get("attributes", {}).get("friendly_name", ""),
            "id": s.get("attributes", {}).get("id"),
            "last_triggered": s.get("attributes", {}).get("last_triggered"),
        }
        for s in states
        if s["entity_id"].startswith("automation.")
    ]
    return _dump({"count": len(items), "automations": items})


@mcp.tool()
async def get_automation(automation_id: str) -> str:
    """Get an automation's config by its numeric id (the `id:` field, not the
    entity_id)."""
    return _dump(await client.rest_get(f"/config/automation/config/{automation_id}"))


@mcp.tool()
async def upsert_automation(automation_id: str, config: dict) -> str:
    """Create or update an automation by id. `config` is the automation body
    (alias, trigger, condition, action, mode, ...). Reloads automations on save."""
    result = await client.rest_post(f"/config/automation/config/{automation_id}", config)
    await client.rest_post("/services/automation/reload", {})
    return _dump(result)


@mcp.tool()
async def delete_automation(automation_id: str) -> str:
    """Delete an automation by id and reload automations."""
    result = await client.rest_delete(f"/config/automation/config/{automation_id}")
    await client.rest_post("/services/automation/reload", {})
    return _dump(result)


@mcp.tool()
async def trigger_automation(entity_id: str, skip_condition: bool = True) -> str:
    """Manually run an automation now."""
    return _dump(await client.rest_post(
        "/services/automation/trigger",
        {"entity_id": entity_id, "skip_condition": skip_condition},
    ))


# --------------------------------------------------------------------- scripts
@mcp.tool()
async def list_scripts() -> str:
    """List all script entities."""
    states = await client.rest_get("/states")
    items = [
        {"entity_id": s["entity_id"], "state": s["state"],
         "friendly_name": s.get("attributes", {}).get("friendly_name", "")}
        for s in states if s["entity_id"].startswith("script.")
    ]
    return _dump({"count": len(items), "scripts": items})


@mcp.tool()
async def get_script(script_id: str) -> str:
    """Get a script's config by its id (the part after 'script.')."""
    return _dump(await client.rest_get(f"/config/script/config/{script_id}"))


@mcp.tool()
async def upsert_script(script_id: str, config: dict) -> str:
    """Create or update a script by id. `config` is the script body (sequence,
    alias, mode, fields, ...). Reloads scripts on save."""
    result = await client.rest_post(f"/config/script/config/{script_id}", config)
    await client.rest_post("/services/script/reload", {})
    return _dump(result)


@mcp.tool()
async def delete_script(script_id: str) -> str:
    """Delete a script by id and reload scripts."""
    result = await client.rest_delete(f"/config/script/config/{script_id}")
    await client.rest_post("/services/script/reload", {})
    return _dump(result)


@mcp.tool()
async def run_script(entity_id: str, variables: dict | None = None) -> str:
    """Run a script now. entity_id like 'script.my_script'."""
    domain, _, obj = entity_id.partition(".")
    return _dump(await client.rest_post(f"/services/script/{obj}", variables or {}))


# ---------------------------------------------------------------------- scenes
@mcp.tool()
async def list_scenes() -> str:
    """List all scene entities."""
    states = await client.rest_get("/states")
    items = [
        {"entity_id": s["entity_id"], "state": s["state"],
         "friendly_name": s.get("attributes", {}).get("friendly_name", ""),
         "id": s.get("attributes", {}).get("id")}
        for s in states if s["entity_id"].startswith("scene.")
    ]
    return _dump({"count": len(items), "scenes": items})


@mcp.tool()
async def get_scene(scene_id: str) -> str:
    """Get a scene's config by its numeric id."""
    return _dump(await client.rest_get(f"/config/scene/config/{scene_id}"))


@mcp.tool()
async def upsert_scene(scene_id: str, config: dict) -> str:
    """Create or update a scene by id. `config` includes name and entities (the
    desired state per entity). Reloads scenes on save."""
    result = await client.rest_post(f"/config/scene/config/{scene_id}", config)
    await client.rest_post("/services/scene/reload", {})
    return _dump(result)


@mcp.tool()
async def delete_scene(scene_id: str) -> str:
    """Delete a scene by id and reload scenes."""
    result = await client.rest_delete(f"/config/scene/config/{scene_id}")
    await client.rest_post("/services/scene/reload", {})
    return _dump(result)


@mcp.tool()
async def activate_scene(entity_id: str) -> str:
    """Activate a scene now. entity_id like 'scene.movie_night'."""
    return _dump(await client.rest_post("/services/scene/turn_on", {"entity_id": entity_id}))
