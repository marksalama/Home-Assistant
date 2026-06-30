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
    if not ha_token:
        raise SystemExit("HA_TOKEN is not set. Create a Long-Lived Access Token in Home Assistant.")

    return Settings(
        ha_url=ha_url,
        ha_token=ha_token,
        verify_ssl=_as_bool(os.environ.get("HA_VERIFY_SSL"), True),
        timeout=float(os.environ.get("HA_TIMEOUT", "30")),
        files_backend=os.environ.get("HA_FILES_BACKEND", "none").strip().lower(),
        config_dir=os.environ.get("HA_CONFIG_DIR"),
        ssh_host=os.environ.get("HA_SSH_HOST"),
        ssh_port=int(os.environ.get("HA_SSH_PORT", "22")),
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
        transport=os.environ.get("HA_TRANSPORT", "stdio").strip().lower(),
        http_host=os.environ.get("HA_HOST", "127.0.0.1").strip(),
        http_port=int(os.environ.get("HA_PORT", "8765")),
        http_token=os.environ.get("HA_HTTP_TOKEN", "").strip() or None,
    )
