"""MCP server exposing broad control over a Home Assistant installation.

Importing `ha_mcp.tools` registers every tool on the shared FastMCP instance
defined in `ha_mcp.app`.
"""

from __future__ import annotations

import os

from . import (
    resources,  # noqa: F401  (import registers MCP resources)
    tools,  # noqa: F401  (import registers all tools)
)
from .app import _apply_tool_filter, mcp, settings
from .tools.discovery import _classify_tools, _enable_tool_search_mode

if settings.disabled_tools or settings.enabled_tools:
    _apply_tool_filter()

# Classify all tools for the discovery proxy (read/write/delete).
_classify_tools()

# Tool-search mode: replace full catalog with discovery entry points + pinned
if os.environ.get("HA_ENABLE_TOOL_SEARCH", "").strip().lower() in ("true", "1"):
    _enable_tool_search_mode()

__all__ = ["mcp"]
