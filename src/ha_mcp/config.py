"""Runtime configuration loaded from environment variables.

A small `.env` file (if present next to where the server is started, or pointed
at via the standard environment) is loaded so users don't have to export every
variable manually.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """Minimal .env loader (no extra dependency).

    Looks for a `.env` file in the current working directory and in the
    repository root, and sets any variables that aren't already in the
    environment. Existing environment variables always win.
    """
    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]
    for path in candidates:
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        raise SystemExit(f"{name} must be a whole number, got {raw!r}.") from None


def _as_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError:
        raise SystemExit(f"{name} must be a number, got {raw!r}.") from None


@dataclass
class Settings:
    ha_url: str
    ha_token: str
    verify_ssl: bool
    timeout: float

    files_backend: str  # "none" | "local" | "ssh"

    # local backend
    config_dir: str | None

    # ssh backend
    ssh_host: str | None
    ssh_port: int
    ssh_user: str | None
    ssh_password: str | None
    ssh_key_file: str | None
    ssh_config_dir: str

    # safety / security
    read_only: bool
    snapshots_enabled: bool
    snapshot_dir: str
    auto_backup_before_update: bool

    # tool filtering
    disabled_tools: set
    enabled_tools: set | None

    # HTTP transport
    transport: str
    http_host: str
    http_port: int
    http_token: str | None
    builtin_mcp_url: str | None

    # new options (keyword defaults keep older Settings(...) call sites working)
    snapshot_keep: int = 30
    log_level: str = "warning"
    ssh_known_hosts: str = str(Path.home() / ".ha-mcp" / "known_hosts")

    @property
    def ws_url(self) -> str:
        base = self.ha_url.rstrip("/")
        if base.startswith("https://"):
            base = "wss://" + base[len("https://"):]
        elif base.startswith("http://"):
            base = "ws://" + base[len("http://"):]
        return base + "/api/websocket"

    @property
    def rest_base(self) -> str:
        return self.ha_url.rstrip("/") + "/api"


def load_settings() -> Settings:
    _load_dotenv()

    ha_url = os.environ.get("HA_URL", "").strip()
    ha_token = os.environ.get("HA_TOKEN", "").strip()
    if not ha_url:
        raise SystemExit("HA_URL is not set. See .env.example for configuration help.")
    if not ha_url.startswith(("http://", "https://")):
        raise SystemExit(
            f"HA_URL must start with http:// or https://, got {ha_url!r} "
            "(example: http://homeassistant.local:8123)."
        )
    if not ha_token:
        raise SystemExit("HA_TOKEN is not set. Create a Long-Lived Access Token in Home Assistant.")

    files_backend = os.environ.get("HA_FILES_BACKEND", "none").strip().lower()
    if files_backend not in {"", "none", "local", "ssh"}:
        raise SystemExit(
            f"HA_FILES_BACKEND must be none, local or ssh, got {files_backend!r}."
        )

    transport = os.environ.get("HA_TRANSPORT", "stdio").strip().lower()
    if transport not in {"stdio", "sse", "http", "streamable-http"}:
        raise SystemExit(
            f"HA_TRANSPORT must be stdio, sse or http, got {transport!r}."
        )

    return Settings(
        ha_url=ha_url,
        ha_token=ha_token,
        verify_ssl=_as_bool(os.environ.get("HA_VERIFY_SSL"), True),
        timeout=_as_float("HA_TIMEOUT", 30.0),
        files_backend=files_backend,
        config_dir=os.environ.get("HA_CONFIG_DIR"),
        ssh_host=os.environ.get("HA_SSH_HOST"),
        ssh_port=_as_int("HA_SSH_PORT", 22),
        ssh_user=os.environ.get("HA_SSH_USER"),
        ssh_password=os.environ.get("HA_SSH_PASSWORD"),
        ssh_key_file=os.environ.get("HA_SSH_KEY_FILE"),
        ssh_config_dir=os.environ.get("HA_SSH_CONFIG_DIR", "/config"),
        read_only=_as_bool(os.environ.get("HA_READ_ONLY"), False),
        snapshots_enabled=_as_bool(os.environ.get("HA_SNAPSHOTS"), True),
        snapshot_dir=os.environ.get(
            "HA_SNAPSHOT_DIR", str(Path.home() / ".ha-mcp" / "snapshots")
        ),
        auto_backup_before_update=_as_bool(
            os.environ.get("HA_AUTO_BACKUP_BEFORE_UPDATE"), False
        ),
        disabled_tools={t.strip() for t in os.environ.get("HA_DISABLED_TOOLS", "").split(",") if t.strip()},
        enabled_tools={t.strip() for t in os.environ.get("HA_ENABLED_TOOLS", "").split(",") if t.strip()} or None,
        transport=transport,
        http_host=os.environ.get("HA_HOST", "127.0.0.1").strip(),
        http_port=_as_int("HA_PORT", 8765),
        http_token=os.environ.get("HA_HTTP_TOKEN", "").strip() or None,
        builtin_mcp_url=os.environ.get("HA_BUILTIN_MCP_URL", "").strip() or None,
        snapshot_keep=_as_int("HA_SNAPSHOT_KEEP", 30),
        log_level=os.environ.get("HA_LOG_LEVEL", "warning").strip().lower(),
        ssh_known_hosts=os.environ.get(
            "HA_SSH_KNOWN_HOSTS", str(Path.home() / ".ha-mcp" / "known_hosts")
        ),
    )
