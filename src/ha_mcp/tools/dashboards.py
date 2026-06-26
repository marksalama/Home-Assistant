"""Lovelace dashboards: list, read and write dashboard configs."""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp


@mcp.tool()
async def list_dashboards() -> str:
    """List all Lovelace dashboards (the extra ones in the sidebar)."""
    return _dump(await client.ws_command({"type": "lovelace/dashboards/list"}))


@mcp.tool()
async def get_dashboard(url_path: str | None = None) -> str:
    """Get a dashboard's full configuration (views and cards).

    Args:
        url_path: The dashboard's url_path (e.g. "home"). Omit for the default
            "Overview" dashboard.
    """
    cmd: dict[str, Any] = {"type": "lovelace/config", "force": True}
    if url_path:
        cmd["url_path"] = url_path
    return _dump(await client.ws_command(cmd))


@mcp.tool()
async def save_dashboard(config: dict, url_path: str | None = None) -> str:
    """Overwrite a dashboard's configuration with `config` (a dict with a
    "views" list). Omit url_path for the default dashboard.

    Note: saving switches that dashboard to storage mode (UI-managed)."""
    cmd: dict[str, Any] = {"type": "lovelace/config/save", "config": config}
    if url_path:
        cmd["url_path"] = url_path
    return _dump(await client.ws_command(cmd))


@mcp.tool()
async def create_dashboard(title: str, url_path: str, icon: str | None = None,
                           show_in_sidebar: bool = True) -> str:
    """Create a new (storage-mode) dashboard that appears in the sidebar.

    Args:
        title: Display title.
        url_path: URL slug, must contain a hyphen, e.g. "my-home".
        icon: Optional mdi icon, e.g. "mdi:home".
        show_in_sidebar: Whether it shows in the sidebar.
    """
    cmd: dict[str, Any] = {
        "type": "lovelace/dashboards/create",
        "title": title,
        "url_path": url_path,
        "show_in_sidebar": show_in_sidebar,
        "mode": "storage",
    }
    if icon:
        cmd["icon"] = icon
    return _dump(await client.ws_command(cmd))
