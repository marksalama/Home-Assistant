"""In-session MCP client setup helpers.

These tools complement the interactive ``ha-mcp-setup`` wizard. They are meant
for users who ask the AI to configure one extra client without rerunning the
whole wizard.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from ..app import _dump, mcp, settings
from ..ha_client import HAError

SUPPORTED_CLIENTS = {
    "claude_code": ".mcp.json",
    "vscode": ".vscode/mcp.json",
    "cursor": "~/.cursor/mcp.json",
    "opencode": "opencode.json",
    "gemini": "~/.gemini/settings.json",
}


def _script_command() -> str:
    found = shutil.which("ha-mcp")
    if found:
        return found
    scripts_dir = Path(sys.executable).parent
    for candidate in (
        scripts_dir / "ha-mcp.exe",
        scripts_dir / "ha-mcp",
        scripts_dir / "ha-mcp.cmd",
        scripts_dir / "ha-mcp.bat",
    ):
        if candidate.exists():
            return str(candidate)
    return "ha-mcp"


def _env() -> dict[str, str]:
    env = {
        "HA_URL": settings.ha_url,
        "HA_TOKEN": settings.ha_token,
        "HA_VERIFY_SSL": "true" if settings.verify_ssl else "false",
        "HA_FILES_BACKEND": settings.files_backend,
        "HA_READ_ONLY": "true" if settings.read_only else "false",
        "HA_SNAPSHOTS": "true" if settings.snapshots_enabled else "false",
        "HA_AUTO_BACKUP_BEFORE_UPDATE": "true" if settings.auto_backup_before_update else "false",
    }
    if settings.config_dir:
        env["HA_CONFIG_DIR"] = settings.config_dir
    if settings.ssh_host:
        env["HA_SSH_HOST"] = settings.ssh_host
        env["HA_SSH_PORT"] = str(settings.ssh_port)
    if settings.ssh_user:
        env["HA_SSH_USER"] = settings.ssh_user
    if settings.ssh_password:
        env["HA_SSH_PASSWORD"] = settings.ssh_password
    if settings.ssh_key_file:
        env["HA_SSH_KEY_FILE"] = settings.ssh_key_file
    if settings.ssh_config_dir:
        env["HA_SSH_CONFIG_DIR"] = settings.ssh_config_dir
    if settings.http_token:
        env["HA_HTTP_TOKEN"] = settings.http_token
    if settings.builtin_mcp_url:
        env["HA_BUILTIN_MCP_URL"] = settings.builtin_mcp_url
    return env


def _redact_env(env: dict[str, str]) -> dict[str, str]:
    secret_keys = {"HA_TOKEN", "HA_SSH_PASSWORD", "HA_HTTP_TOKEN"}
    return {key: ("<secret>" if key in secret_keys else value) for key, value in env.items()}


def _mcp_entry(transport: str) -> dict[str, Any]:
    if transport == "stdio":
        return {"command": _script_command(), "env": _env()}
    if transport == "http":
        return {
            "url": f"http://{settings.http_host}:{settings.http_port}/mcp",
            "headers": (
                {"Authorization": f"Bearer {settings.http_token}"}
                if settings.http_token
                else {}
            ),
        }
    raise HAError("transport must be 'stdio' or 'http'.")


def _write_json_config(path: Path, server_name: str, entry: dict[str, Any]) -> None:
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}
    existing.setdefault("mcpServers", {})[server_name] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except (OSError, NotImplementedError):
        pass


def _target_path(client: str) -> Path:
    if client == "claude_code":
        return Path.cwd() / ".mcp.json"
    if client == "vscode":
        return Path.cwd() / ".vscode" / "mcp.json"
    if client == "cursor":
        return Path.home() / ".cursor" / "mcp.json"
    if client == "opencode":
        return Path.cwd() / "opencode.json"
    if client == "gemini":
        return Path.home() / ".gemini" / "settings.json"
    raise HAError(f"client must be one of {sorted(SUPPORTED_CLIENTS)}.")


@mcp.tool()
async def get_mcp_install_options() -> str:
    """Show supported client installers and the current safe defaults."""
    return _dump(
        {
            "clients": SUPPORTED_CLIENTS,
            "recommended": "claude_code",
            "transports": {
                "stdio": "Best for local clients; secrets stay in the client config.",
                "http": "Best for remote/multiple clients; use HA_HTTP_TOKEN.",
            },
            "current": {
                "transport": settings.transport,
                "http_url": f"http://{settings.http_host}:{settings.http_port}/mcp",
                "http_auth_enabled": bool(settings.http_token),
                "files_backend": settings.files_backend,
                "read_only": settings.read_only,
            },
        }
    )


@mcp.tool()
async def install_mcp_tools(
    client: str = "claude_code",
    transport: str = "stdio",
    write_files: bool = False,
    confirm: bool = False,
) -> str:
    """Generate or write MCP client configuration for Home Assistant MCP.

    Args:
        client: One of claude_code, vscode, cursor, opencode, gemini.
        transport: "stdio" or "http".
        write_files: If false, only returns a redacted preview.
        confirm: Required when write_files=true because secrets may be written.
    """
    client = client.strip().lower().replace("-", "_")
    if client not in SUPPORTED_CLIENTS:
        raise HAError(f"client must be one of {sorted(SUPPORTED_CLIENTS)}.")
    entry = _mcp_entry(transport)
    preview = json.loads(json.dumps(entry))
    if "env" in preview:
        preview["env"] = _redact_env(preview["env"])
    if preview.get("headers", {}).get("Authorization"):
        preview["headers"]["Authorization"] = "Bearer <secret>"

    if not write_files:
        return _dump(
            {
                "client": client,
                "transport": transport,
                "write_files": False,
                "target": str(_target_path(client)),
                "preview": preview,
                "next_step": "Call again with write_files=true and confirm=true to write the config.",
            }
        )

    if not confirm:
        raise HAError("Refusing to write client config without confirm=True.")

    path = _target_path(client)
    server_name = "home-assistant" if client != "gemini" else "homeassistant"
    _write_json_config(path, server_name, entry)
    return _dump(
        {
            "ok": True,
            "client": client,
            "transport": transport,
            "written": str(path),
            "secret_note": "Secrets were written to the local client config and were not returned in this response.",
        }
    )
