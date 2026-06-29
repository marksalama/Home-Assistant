"""Raw YAML/config file access (optional local or ssh backend).

Writes and deletes automatically snapshot the previous file contents to a local
store, so any change can be rolled back with `restore_config_file`.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict

from ..app import _dump, _files, client, mcp, settings, snapshots
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


def _guard_file_write(action: str) -> None:
    if settings.read_only:
        raise HAError(
            "Server is in read-only mode (HA_READ_ONLY=true); "
            f"refusing to change Home Assistant files: {action}"
        )


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
    _guard_file_write(f"write {path}")
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
    _guard_file_write(f"delete {path}")
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
    _guard_file_write(f"restore {path}")
    backend = _files()
    restored = await asyncio.to_thread(snapshots.read, path, version)
    await _snapshot_existing(backend, path)  # so the restore can be undone too
    await asyncio.to_thread(backend.write, path, restored)
    return _dump({"ok": True, "path": path, "restored_version": version or "latest",
                   "bytes": len(restored.encode("utf-8"))})


@mcp.tool()
async def set_yaml_key(
    path: str,
    key: str,
    value: str | None = None,
    confirm: bool = False,
    validate: bool = True,
) -> str:
    """Add, replace or remove a top-level YAML key in a config file. Safer than
    write_config_file because it only touches one key.

    ``value=None`` removes the key entirely. The previous version is snapshotted
    and ``check_config`` is run afterwards (unless validate=False).

    Args:
        path: Config file relative path, e.g. "configuration.yaml".
        key: Top-level YAML key, e.g. "sensor", "template", "automation".
        value: YAML value as a string (will be placed under the key with proper
            indentation). Omit or set to None to remove the key.
        confirm: Required for removal.
        validate: Run check_config afterwards (default True).

    Requires HA_FILES_BACKEND=local or ssh. Works without extra deps for simple
    keys; install ``ruamel.yaml`` (``pip install home-assistant-mcp[yaml]``) for
    full YAML round-trip fidelity.
    """
    if value is None and not confirm:
        raise HAError("Refusing to remove a YAML key without confirm=True.")
    _guard_file_write(f"set_yaml_key {key} in {path}")
    backend = _files()
    content = await asyncio.to_thread(backend.read, path)

    lines = content.splitlines(keepends=True)
    result_lines: list[str] = []

    # --- attempt: use a YAML library for precise editing ---
    have_yaml = False
    try:
        from ruamel.yaml import YAML  # type: ignore[import-not-found]
        yaml_lib = YAML()
        have_yaml = True
    except ImportError:
        try:
            import yaml as yaml_mod  # type: ignore[import-not-found, no-redef]
            have_yaml = True
            yaml_lib = yaml_mod  # pyyaml
        except ImportError:
            pass

    if have_yaml:
        # Round-trip via the YAML library
        parsed = yaml_lib.load(content)
        if parsed is None:
            parsed = {}
        if value is None:
            parsed.pop(key, None)
        else:
            val_parsed = yaml_lib.load(value)
            parsed[key] = val_parsed if val_parsed is not None else value
        from io import StringIO
        buf = StringIO()
        if hasattr(yaml_lib, 'dump'):
            yaml_lib.dump(parsed, buf)
        else:
            yaml_lib.dump(parsed, buf, default_flow_style=False)
        new_content = buf.getvalue()
        await _snapshot_existing(backend, path)
        await asyncio.to_thread(backend.write, path, new_content)
    else:
        # --- fallback: string-based top-level key replacement ---
        import re
        indent = ""
        new_lines: list[str] = []

        if value is not None:
            # split the value into indented lines (4 spaces per level)
            value_lines = value.splitlines()
            if len(value_lines) == 1 and not value_lines[0].strip().startswith("-"):
                # simple scalar
                new_block = f"{indent}{key}: {value.strip()}\n"
            else:
                new_block = f"{indent}{key}: {value_lines[0].strip()}\n"
                for vl in value_lines[1:]:
                    new_block += f"      {vl}\n" if vl.strip() else "\n"

        # find key boundaries
        key_pattern = re.compile(rf"^{key}\s*:")
        start = None
        end = len(lines)
        for i, line in enumerate(lines):
            if start is None:
                if key_pattern.match(line):
                    start = i
            elif start is not None:
                # next non-empty, non-indented line = new top-level key
                stripped = line.rstrip("\n").rstrip("\r")
                if stripped and not stripped[0].isspace() and not stripped.startswith("#"):
                    end = i
                    break

        if value is not None:
            # replace existing or append
            if start is not None:
                result = lines[:start] + [new_block] + lines[end:]
            else:
                # append before first empty line or at the end
                insert_at = len(lines)
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].strip():
                        insert_at = i + 1
                        break
                if insert_at < len(lines) and not lines[insert_at - 1].rstrip("\n").rstrip("\r"):
                    insert_at -= 1
                result = lines[:insert_at] + ["\n", new_block] + lines[insert_at:]
        else:
            # remove key
            if start is None:
                return _dump({"ok": True, "path": path, "key": key, "note": "key not found, nothing removed"})
            result = lines[:start] + lines[end:]

        new_content = "".join(result)
        await _snapshot_existing(backend, path)
        await asyncio.to_thread(backend.write, path, new_content)

    outcome = {"ok": True, "path": path, "key": key, "action": "removed" if value is None else "set",
               "snapshot_saved": snapshots is not None,
               "yaml_library_used": have_yaml}

    if validate and value is not None:
        try:
            check_result = await client.rest_post("/config/core/check_config", {}, write=False)
            outcome["check_config"] = check_result
        except Exception as exc:
            outcome["check_config_error"] = str(exc)

    return _dump(outcome)
