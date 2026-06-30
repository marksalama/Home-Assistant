"""Theme management via Home Assistant's frontend integration."""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp
from ..ha_client import HAError


@mcp.tool()
async def list_themes() -> str:
    """List Home Assistant frontend themes and current defaults."""
    return _dump(await client.ws_command({"type": "frontend/get_themes"}))


@mcp.tool()
async def manage_theme(
    action: str,
    name: str | None = None,
    mode: str | None = None,
) -> str:
    """Manage Home Assistant themes.

    Args:
        action: "list", "set", or "reload".
        name: Theme name for action="set". Use "default" for the default theme.
        mode: Optional mode for action="set": "light" or "dark".
    """
    action = action.strip().lower()
    if action == "list":
        return await list_themes()
    if action == "reload":
        return _dump(await client.rest_post("/services/frontend/reload_themes", {}))
    if action == "set":
        if not name:
            raise HAError("name is required when action='set'.")
        data: dict[str, Any] = {"name": name}
        if mode is not None:
            mode = mode.strip().lower()
            if mode not in {"light", "dark"}:
                raise HAError("mode must be 'light' or 'dark'.")
            data["mode"] = mode
        return _dump(await client.rest_post("/services/frontend/set_theme", data))
    raise HAError("action must be one of: list, set, reload.")
