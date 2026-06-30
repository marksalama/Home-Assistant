"""Friendly interactive setup wizard.

Run after installing the package:  ha-mcp-setup

It walks a non-technical user through:
  1. Entering their Home Assistant address + access token (opens the token page).
  2. Testing the connection.
  3. Optionally enabling raw YAML file access over SSH.
  4. Writing .env and .mcp.json.
  5. Registering the server with the Claude Code CLI (if installed).
  6. Optionally creating the 'Claude Link' dashboard automatically.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from .config import Settings
from .dashboard_template import build_dashboard
from .ha_client import HAClient


CLAUDE_LINK_SUFFIX_MAP = {
    "connected": "_connected",
    "last_activity": "_last_activity",
    "tool_calls": "_tool_calls",
    "heartbeat_age": "_heartbeat_age",
    "source": "_source",
    "calls_per_minute": "_calls_per_minute",
    "read_only": "_read_only",
    "http_auth": "_http_auth",
    "file_access_enabled": "_file_access_enabled",
    "file_access": "_files_backend",
    "transport": "_transport",
    "mcp_version": "_mcp_version",
    "tools_total": "_tools_total",
    "disabled_tools": "_disabled_tools",
    "enabled_tools": "_enabled_tools",
    "create_backup": "_create_backup",
    "reset_stats": "_reset_stats",
    "reload_integration": "_reload_integration",
}


def _ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def _ask_yes(prompt: str, default: bool = True) -> bool:
    d = "J/n" if default else "j/N"
    value = input(f"{prompt} ({d}): ").strip().lower()
    if not value:
        return default
    return value in {"j", "ja", "y", "yes"}


def _configure_output() -> None:
    """Avoid UnicodeEncodeError on Windows consoles/pipes with legacy encodings."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def _is_local(url: str) -> bool:
    parsed = urlparse(url if "://" in url else f"//{url}")
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def _host_only(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"//{value}")
    return (parsed.hostname or value).strip().strip("/")


def _secure(path: Path) -> None:
    """Restrict a secrets file to the current user (best effort, no-op on Windows)."""
    try:
        path.chmod(0o600)
    except (OSError, NotImplementedError):
        pass


def _make_settings(values: dict) -> Settings:
    return Settings(
        ha_url=values["HA_URL"],
        ha_token=values["HA_TOKEN"],
        verify_ssl=values.get("HA_VERIFY_SSL", "true").lower() != "false",
        timeout=30.0,
        files_backend=values.get("HA_FILES_BACKEND", "none"),
        config_dir=values.get("HA_CONFIG_DIR"),
        ssh_host=values.get("HA_SSH_HOST"),
        ssh_port=int(values.get("HA_SSH_PORT", "22")),
        ssh_user=values.get("HA_SSH_USER"),
        ssh_password=values.get("HA_SSH_PASSWORD"),
        ssh_key_file=values.get("HA_SSH_KEY_FILE"),
        ssh_config_dir=values.get("HA_SSH_CONFIG_DIR", "/config"),
        read_only=values.get("HA_READ_ONLY", "false").lower() == "true",
        snapshots_enabled=values.get("HA_SNAPSHOTS", "true").lower() != "false",
        snapshot_dir=values.get("HA_SNAPSHOT_DIR", str(Path.home() / ".ha-mcp" / "snapshots")),
        auto_backup_before_update=values.get("HA_AUTO_BACKUP_BEFORE_UPDATE", "false").lower() == "true",
        disabled_tools={t.strip() for t in values.get("HA_DISABLED_TOOLS", "").split(",") if t.strip()},
        enabled_tools={t.strip() for t in values.get("HA_ENABLED_TOOLS", "").split(",") if t.strip()} or None,
        transport=values.get("HA_TRANSPORT", "stdio"),
        http_host=values.get("HA_HOST", "127.0.0.1"),
        http_port=int(values.get("HA_PORT", "8765")),
        http_token=values.get("HA_HTTP_TOKEN") or None,
        builtin_mcp_url=values.get("HA_BUILTIN_MCP_URL") or None,
    )


async def _test_connection(settings: Settings) -> dict:
    client = HAClient(settings)
    try:
        return await client.rest_get("/config")
    finally:
        await client.aclose()


async def _create_dashboard(settings: Settings) -> None:
    client = HAClient(settings)
    try:
        entity_ids: dict[str, str] = {}
        try:
            registry = await client.ws_command({"type": "config/entity_registry/list"})
            for entry in registry if isinstance(registry, list) else []:
                if entry.get("platform") != "claude_link":
                    continue
                unique_id = str(entry.get("unique_id") or "")
                for key, suffix in CLAUDE_LINK_SUFFIX_MAP.items():
                    if unique_id.endswith(suffix):
                        entity_ids[key] = entry.get("entity_id")
        except Exception:
            pass

        existing = await client.ws_command({"type": "lovelace/dashboards/list"})
        if not any(d.get("url_path") == "claude-link" for d in existing):
            await client.ws_command(
                {
                    "type": "lovelace/dashboards/create",
                    "title": "Claude Link",
                    "url_path": "claude-link",
                    "icon": "mdi:robot-happy",
                    "show_in_sidebar": True,
                    "mode": "storage",
                }
            )
        await client.ws_command(
                {
                    "type": "lovelace/config/save",
                    "url_path": "claude-link",
                    "config": build_dashboard(entity_ids),
                }
        )
    finally:
        await client.aclose()


async def _make_backup(settings) -> None:
    client = HAClient(settings)
    try:
        services = await client.rest_get("/services")
        hassio_services = next(
            (
                service.get("services", {})
                for service in services
                if service.get("domain") == "hassio"
            ),
            {},
        )
        backup_services = next(
            (
                service.get("services", {})
                for service in services
                if service.get("domain") == "backup"
            ),
            {},
        )
        if "backup_full" in hassio_services:
            await client.rest_post(
                "/services/hassio/backup_full",
                {"name": "Voor Claude Code", "compressed": True},
            )
        elif "create_automatic" in backup_services:
            await client.rest_post("/services/backup/create_automatic", {})
        elif "create" in backup_services:
            await client.rest_post("/services/backup/create", {"name": "Voor Claude Code"})
        else:
            await client.rest_post("/hassio/backups/new/full", {"name": "Voor Claude Code"})
    finally:
        await client.aclose()


def _write_env(values: dict, path: Path) -> None:
    lines = ["# Generated by ha-mcp-setup", ""]
    for key in (
        "HA_URL", "HA_TOKEN", "HA_VERIFY_SSL", "HA_FILES_BACKEND",
        "HA_CONFIG_DIR", "HA_SSH_HOST", "HA_SSH_PORT", "HA_SSH_USER",
        "HA_SSH_PASSWORD", "HA_SSH_KEY_FILE", "HA_SSH_CONFIG_DIR",
        "HA_READ_ONLY", "HA_SNAPSHOTS", "HA_AUTO_BACKUP_BEFORE_UPDATE",
        "HA_TRANSPORT", "HA_HOST", "HA_PORT", "HA_HTTP_TOKEN",
        "HA_BUILTIN_MCP_URL",
    ):
        if values.get(key):
            lines.append(f"{key}={values[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_mcp_json(values: dict, command: str, path: Path) -> None:
    env = {k: v for k, v in values.items() if v}
    config = {"mcpServers": {"home-assistant": {"command": command, "env": env}}}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            existing.setdefault("mcpServers", {})["home-assistant"] = config["mcpServers"]["home-assistant"]
            config = existing
        except (json.JSONDecodeError, OSError):
            pass
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _script_command(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found

    scripts_dir = Path(sys.executable).parent
    candidates = [
        scripts_dir / f"{name}.exe",
        scripts_dir / name,
        scripts_dir / f"{name}.cmd",
        scripts_dir / f"{name}.bat",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return name


def _register_with_claude(values: dict, command: str) -> bool:
    claude = shutil.which("claude")
    if not claude:
        return False
    args = [claude, "mcp", "add", "home-assistant"]
    for key, val in values.items():
        if val:
            args += ["--env", f"{key}={val}"]
    args += ["--", command]
    try:
        subprocess.run(args, check=True)
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


# ---------------------------------------------------------- multi-client configs
_CLIENT_CHOICES: dict[str, str] = {
    "1": "Claude Code",
    "2": "Claude Desktop",
    "3": "Gemini CLI",
    "4": "Cursor",
    "5": "VSCode / GitHub Copilot",
    "6": "Open WebUI",
    "7": "Antigravity CLI",
    "8": "OpenCode",
    "9": "ChatGPT (remote)",
}


def _pick_clients() -> list[str]:
    print("\n📋 Voor welke AI-clients wil je de MCP-server instellen?\n")
    for key, label in _CLIENT_CHOICES.items():
        print(f"  {key}. {label}")
    print("  0.  Alle bovenstaande")
    print()
    raw = _ask("Kies nummers (komma-gescheiden, bijv. 1,2)", "1")
    if raw.strip() == "0":
        return list(_CLIENT_CHOICES.keys())
    chosen = [k.strip() for k in raw.split(",") if k.strip() in _CLIENT_CHOICES]
    return chosen or ["1"]


def _write_claude_desktop_config(values: dict, command: str) -> str | None:
    """Write Claude Desktop config (~/Library/... or %APPDATA%/...)."""
    home = Path.home()
    if sys.platform == "win32":
        config_dir = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))) / "Claude"
    elif sys.platform == "darwin":
        config_dir = home / "Library" / "Application Support" / "Claude"
    else:
        config_dir = home / ".config" / "Claude"
    config_path = config_dir / "claude_desktop_config.json"
    if not config_dir.exists():
        return f"⚠️  Claude Desktop config-map niet gevonden: {config_dir}"
    env = {k: v for k, v in values.items() if v}
    entry = {"command": command, "env": env}
    existing = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    existing.setdefault("mcpServers", {})["home-assistant"] = entry
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return f"✅ Claude Desktop: {config_path}"


def _write_gemini_cli_config(values: dict, command: str) -> str | None:
    """Write Gemini CLI config (~/.gemini/settings.json)."""
    home = Path.home()
    config_dir = home / ".gemini"
    config_path = config_dir / "settings.json"
    env = {k: v for k, v in values.items() if v}
    entry = {"command": command, "env": env, "type": "stdio"}
    existing = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    existing.setdefault("mcpServers", {})["home-assistant"] = entry
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return f"✅ Gemini CLI: {config_path}"


def _write_cursor_config(values: dict, command: str) -> str | None:
    """Write Cursor MCP config (~/.cursor/mcp.json)."""
    home = Path.home()
    config_dir = home / ".cursor"
    config_path = config_dir / "mcp.json"
    _write_mcp_json(values, command, config_path)
    return f"✅ Cursor: {config_path}"


def _write_vscode_config(values: dict, command: str) -> str | None:
    """Write VSCode / Copilot MCP config (.vscode/mcp.json)."""
    cwd = Path.cwd()
    config_dir = cwd / ".vscode"
    config_path = config_dir / "mcp.json"
    config_dir.mkdir(parents=True, exist_ok=True)
    _write_mcp_json(values, command, config_path)
    return f"✅ VSCode: {config_path}"


def _write_openwebui_config(values: dict, command: str) -> str | None:
    """Print Open WebUI instructions (URL-based config)."""
    print("ℹ️  Open WebUI: configureer via Settings → MCP Servers →")
    print(f"    URL: http://localhost:{values.get('HA_PORT', '8765')}/mcp")
    print("    (zet HA_TRANSPORT=http voor je de server start)")
    return None


def _write_chatgpt_config(values: dict, command: str) -> str | None:
    """Print ChatGPT instructions."""
    ha_url = values.get("HA_URL", "").rstrip("/")
    print("ℹ️  ChatGPT: ga naar Workspace settings → Apps → Create →")
    print(f"    MCP Server URL: {ha_url}/api/mcp  (of http://localhost:8765/mcp lokaal)")
    return None


def _write_antigravity_config(values: dict, command: str) -> str | None:
    """Write Antigravity CLI config (~/.gemini/antigravity-cli/mcp_config.json)."""
    home = Path.home()
    config_dir = home / ".gemini" / "antigravity-cli"
    config_path = config_dir / "mcp_config.json"
    env = {k: v for k, v in values.items() if v}
    entry = {"command": command, "env": env}
    existing = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    existing.setdefault("mcpServers", {})["homeassistant"] = entry
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return f"✅ Antigravity CLI: {config_path}"


def _write_opencode_config(values: dict, command: str) -> str | None:
    """Write OpenCode config (opencode.json)."""
    cwd = Path.cwd()
    config_path = cwd / "opencode.json"
    env = {k: v for k, v in values.items() if v}
    entry = {"command": command, "env": env}
    existing: dict = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    existing.setdefault("mcpServers", {})["home-assistant"] = entry
    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return f"✅ OpenCode: {config_path}"


_CLIENT_WRITERS = {
    "1": ("Claude Code", _register_with_claude),
    "2": ("Claude Desktop", _write_claude_desktop_config),
    "3": ("Gemini CLI", _write_gemini_cli_config),
    "4": ("Cursor", _write_cursor_config),
    "5": ("VSCode / Copilot", _write_vscode_config),
    "6": ("Open WebUI", _write_openwebui_config),
    "7": ("Antigravity CLI", _write_antigravity_config),
    "8": ("OpenCode", _write_opencode_config),
    "9": ("ChatGPT", _write_chatgpt_config),
}


def _configure_clients(values: dict, command: str, chosen: list[str]) -> None:
    for key in chosen:
        label, writer = _CLIENT_WRITERS[key]
        print(f"\n⚙️  {label} configureren...")
        try:
            result = writer(values, command)
            if result:
                print(result)
        except Exception as exc:
            print(f"⚠️  Kon {label} niet configureren: {exc}")


def main() -> None:
    _configure_output()
    print("\n=== Home Assistant ↔ Claude Code setup ===\n")
    values: dict = {}

    # 1. Address + token
    values["HA_URL"] = _ask("Webadres van Home Assistant", "http://homeassistant.local:8123")
    print("\nIk open nu de pagina waar je een token kunt aanmaken.")
    print("Klik onderaan op 'Token aanmaken', geef het de naam 'claude-code' en kopieer het.")
    try:
        webbrowser.open(values["HA_URL"].rstrip("/") + "/profile/security")
    except Exception:
        pass
    values["HA_TOKEN"] = _ask("\nPlak hier je token")
    if values["HA_URL"].startswith("https://") and not _ask_yes(
        "Gebruik je een geldig (niet zelf-ondertekend) certificaat?", True
    ):
        values["HA_VERIFY_SSL"] = "false"
    elif values["HA_URL"].startswith("http://") and not _is_local(values["HA_URL"]):
        print("\n⚠️  Beveiligingstip: je gebruikt een onversleutelde (http) verbinding")
        print("    naar een adres buiten je eigen netwerk. Je token reist dan onbeschermd.")
        print("    Gebruik bij voorkeur een https-adres (bijv. via Nabu Casa of een reverse proxy).")

    # 2. Test
    print("\nVerbinding testen...")
    try:
        info = asyncio.run(_test_connection(_make_settings(values)))
        print(f"✅ Verbonden met Home Assistant {info.get('version')} ({info.get('location_name')}).")
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Kon geen verbinding maken: {exc}")
        print("Controleer het adres en token en probeer opnieuw.")
        sys.exit(1)

    # 3. File access
    if _ask_yes("\nWil je dat Claude ook YAML-bestanden kan bewerken (aanrader)?", True):
        print("Hiervoor gebruik je de 'Advanced SSH & Web Terminal' add-on in Home Assistant.")
        values["HA_FILES_BACKEND"] = "ssh"
        default_ssh_host = _host_only(values["HA_URL"])
        values["HA_SSH_HOST"] = _host_only(_ask("SSH-adres", default_ssh_host))
        values["HA_SSH_PORT"] = _ask("SSH-poort", "22")
        values["HA_SSH_USER"] = _ask("SSH-gebruiker", "root")
        if _ask_yes("Inloggen met een SSH-sleutel i.p.v. wachtwoord (veiliger)?", False):
            values["HA_SSH_KEY_FILE"] = _ask("Pad naar je private key", str(Path.home() / ".ssh" / "id_ed25519"))
        else:
            values["HA_SSH_PASSWORD"] = _ask("SSH-wachtwoord (van de add-on)")
        values["HA_SSH_CONFIG_DIR"] = "/config"
        # Snapshots make file edits reversible; keep them on by default.
        values["HA_SNAPSHOTS"] = "true"
    else:
        values["HA_FILES_BACKEND"] = "none"

    # 3b. Safety choices
    if _ask_yes("\nVeilige modus aanzetten (Claude mag alles LEZEN maar niets WIJZIGEN)?", False):
        values["HA_READ_ONLY"] = "true"
        print("   → Veilige modus AAN. Zet later HA_READ_ONLY=false om wijzigingen toe te staan.")
    if _ask_yes("Automatisch een back-up maken vóór elke update (aanrader)?", True):
        values["HA_AUTO_BACKUP_BEFORE_UPDATE"] = "true"

    # 4. Pick clients
    chosen = _pick_clients()

    # 5. Write base config files
    cwd = Path.cwd()
    env_path = cwd / ".env"
    mcp_path = cwd / ".mcp.json"
    _write_env(values, env_path)
    command = _script_command("ha-mcp")
    _write_mcp_json(values, command, mcp_path)
    _secure(env_path)
    _secure(mcp_path)
    print(f"\n✅ Basisconfiguratie opgeslagen in {env_path} en {mcp_path}.")

    # 6. Configure selected clients
    _configure_clients(values, command, chosen)

    # 7. Dashboard
    if _ask_yes("\nWil je het 'Claude Link' dashboard automatisch aanmaken in Home Assistant?", True):
        try:
            asyncio.run(_create_dashboard(_make_settings(values)))
            print("✅ Dashboard 'Claude Link' aangemaakt (zie de zijbalk in Home Assistant).")
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️  Kon het dashboard niet aanmaken: {exc}")

    # 8. Optional baseline backup
    if _ask_yes("\nWil je nu meteen een back-up van Home Assistant maken als veilig startpunt?", True):
        try:
            asyncio.run(_make_backup(_make_settings(values)))
            print("✅ Back-up gestart in Home Assistant (Instellingen → Systeem → Back-ups).")
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️  Kon geen back-up maken (alleen op HA OS/Supervised): {exc}")

    print("\nKlaar! 🎉")
    print("Tip: installeer ook de 'Claude Link' integratie via HACS voor de status-tegels.")
    print("Herstart je AI-client en check of 'home-assistant' verbonden is.\n")


if __name__ == "__main__":
    main()
