"""MCP server exposing broad control over a Home Assistant installation.

Importing `ha_mcp.tools` registers every tool on the shared FastMCP instance
defined in `ha_mcp.app`.
"""

from __future__ import annotations

from .app import mcp
from . import tools  # noqa: F401  (import registers all tools)

__all__ = ["mcp"]
