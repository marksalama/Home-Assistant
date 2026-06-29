"""MCP server exposing broad control over a Home Assistant installation.

Importing `ha_mcp.tools` registers every tool on the shared FastMCP instance
defined in `ha_mcp.app`.
"""

from __future__ import annotations

from .app import mcp, settings, _apply_tool_filter
from . import tools  # noqa: F401  (import registers all tools)
from . import resources  # noqa: F401  (import registers MCP resources)

if settings.disabled_tools or settings.enabled_tools:
    _apply_tool_filter()

# Classify all tools for the discovery proxy (read/write/delete).
from .tools.discovery import _classify_tools
_classify_tools()

# Tool-search mode: replace full catalog with discovery entry points + pinned
import os as _os
if _os.environ.get("HA_ENABLE_TOOL_SEARCH", "").strip().lower() in ("true", "1"):
    from .tools.discovery import _enable_tool_search_mode
    _enable_tool_search_mode()

__all__ = ["mcp"]
