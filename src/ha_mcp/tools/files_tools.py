"""Raw YAML/config file access (optional local or ssh backend).

Writes and deletes automatically snapshot the previous file contents to a local
store, so any change can be rolled back with `restore_config_file`.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict

from ..app import _dump, _files, mcp, snapshots
from ..ha_client import HAError


async def _snapshot_existing(backend, path: str) -> None:
    """Save the current contents of `path` (if it exists) before changing it."""
    if snapshots is None:
        return
    try:
        current = await asyncio.to_thread(backend.read, path)
    except Exception:
        return  # file doesn't exist yet or unreadable; nothing to snapshot
    await asyncio.to_thread(snapshots.save, path, current)


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

    The previous version is snapshotted first so you can roll back with
    restore_config_file. After editing core YAML, call check_config() before
    restart_home_assistant(). Requires HA_FILES_BACKEND=local or ssh.
    """
    backend = _files()
    await _snapshot_existing(backend, path)
    await asyncio.to_thread(backend.write, path, content)
    return _dump({"ok": True, "path": path, "bytes": len(content.encode("utf-8")),
                  "snapshot_saved": snapshots is not None})


@mcp.tool()
async def delete_config_file(path: str, confirm: bool = False) -> str:
    """Delete a file from the HA config directory. Requires confirm=True.

    The file is snapshotted first so it can be restored. Requires
    HA_FILES_BACKEND=local or ssh.
    """
    if not confirm:
        raise HAError("Refusing to delete without confirm=True.")
    backend = _files()
    await _snapshot_existing(backend, path)
    await asyncio.to_thread(backend.delete, path)
    return _dump({"ok": True, "deleted": path, "snapshot_saved": snapshots is not None})


@mcp.tool()
async def list_file_snapshots(path: str) -> str:
    """List saved snapshots (previous versions) for a config file, newest first."""
    if snapshots is None:
        raise HAError("Snapshots are disabled (HA_SNAPSHOTS=false).")
    versions = await asyncio.to_thread(snapshots.list, path)
    return _dump([asdict(v) for v in versions])


@mcp.tool()
async def restore_config_file(path: str, version: str | None = None) -> str:
    """Roll back a config file to a previous snapshot (latest if version omitted).

    The current contents are snapshotted first, so a restore is itself
    reversible. Requires HA_FILES_BACKEND=local or ssh.
    """
    if snapshots is None:
        raise HAError("Snapshots are disabled (HA_SNAPSHOTS=false).")
    backend = _files()
    restored = await asyncio.to_thread(snapshots.read, path, version)
    await _snapshot_existing(backend, path)  # so the restore can be undone too
    await asyncio.to_thread(backend.write, path, restored)
    return _dump({"ok": True, "path": path, "restored_version": version or "latest",
                  "bytes": len(restored.encode("utf-8"))})
