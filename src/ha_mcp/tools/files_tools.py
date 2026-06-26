"""Raw YAML/config file access (optional local or ssh backend)."""

from __future__ import annotations

import asyncio
from dataclasses import asdict

from ..app import _dump, _files, mcp
from ..ha_client import HAError


@mcp.tool()
async def list_config_files(path: str = "") -> str:
    """List files/folders in the HA config directory (relative path, "" = root).

    Requires HA_FILES_BACKEND=local or ssh.
    """
    backend = _files()
    entries = await asyncio.to_thread(backend.list_dir, path)
    return _dump([asdict(e) for e in entries])


@mcp.tool()
async def read_config_file(path: str) -> str:
    """Read a text/YAML file from the HA config directory.

    Requires HA_FILES_BACKEND=local or ssh.
    """
    backend = _files()
    return await asyncio.to_thread(backend.read, path)


@mcp.tool()
async def write_config_file(path: str, content: str) -> str:
    """Write (create/overwrite) a text/YAML file in the HA config directory.

    After editing core YAML, call check_config() before restart_home_assistant().
    Requires HA_FILES_BACKEND=local or ssh.
    """
    backend = _files()
    await asyncio.to_thread(backend.write, path, content)
    return _dump({"ok": True, "path": path, "bytes": len(content.encode("utf-8"))})


@mcp.tool()
async def delete_config_file(path: str, confirm: bool = False) -> str:
    """Delete a file from the HA config directory. Requires confirm=True.

    Requires HA_FILES_BACKEND=local or ssh.
    """
    if not confirm:
        raise HAError("Refusing to delete without confirm=True.")
    backend = _files()
    await asyncio.to_thread(backend.delete, path)
    return _dump({"ok": True, "deleted": path})
