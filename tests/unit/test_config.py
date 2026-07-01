"""Unit tests for settings loading and validation."""

from __future__ import annotations

import pytest

from ha_mcp.config import Settings, _as_bool, load_settings

BASE_ENV = {
    "HA_URL": "http://homeassistant.local:8123",
    "HA_TOKEN": "token123",
}


def _set_env(monkeypatch, extra: dict[str, str] | None = None) -> None:
    # Clear all HA_* vars so the developer's own environment can't leak in.
    import os

    for key in list(os.environ):
        if key.startswith("HA_"):
            monkeypatch.delenv(key, raising=False)
    for key, value in {**BASE_ENV, **(extra or {})}.items():
        monkeypatch.setenv(key, value)


class TestAsBool:
    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
    def test_truthy(self, value: str) -> None:
        assert _as_bool(value, False) is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", "banana"])
    def test_falsy(self, value: str) -> None:
        assert _as_bool(value, True) is False

    def test_default(self) -> None:
        assert _as_bool(None, True) is True
        assert _as_bool(None, False) is False


class TestLoadSettings:
    def test_minimal(self, monkeypatch) -> None:
        _set_env(monkeypatch)
        s = load_settings()
        assert s.ha_url == BASE_ENV["HA_URL"]
        assert s.transport == "stdio"
        assert s.read_only is False
        assert s.snapshot_keep == 30

    def test_missing_url(self, monkeypatch) -> None:
        _set_env(monkeypatch)
        monkeypatch.delenv("HA_URL")
        with pytest.raises(SystemExit):
            load_settings()

    def test_url_without_scheme_rejected(self, monkeypatch) -> None:
        _set_env(monkeypatch, {"HA_URL": "homeassistant.local:8123"})
        with pytest.raises(SystemExit):
            load_settings()

    def test_invalid_port_gives_clear_error(self, monkeypatch) -> None:
        _set_env(monkeypatch, {"HA_PORT": "not-a-number"})
        with pytest.raises(SystemExit):
            load_settings()

    def test_invalid_transport_rejected(self, monkeypatch) -> None:
        _set_env(monkeypatch, {"HA_TRANSPORT": "carrier-pigeon"})
        with pytest.raises(SystemExit):
            load_settings()

    def test_invalid_files_backend_rejected(self, monkeypatch) -> None:
        _set_env(monkeypatch, {"HA_FILES_BACKEND": "ftp"})
        with pytest.raises(SystemExit):
            load_settings()

    def test_tool_filters(self, monkeypatch) -> None:
        _set_env(monkeypatch, {"HA_DISABLED_TOOLS": "reboot_host, restore_backup"})
        s = load_settings()
        assert s.disabled_tools == {"reboot_host", "restore_backup"}
        assert s.enabled_tools is None


class TestUrls:
    def _settings(self, url: str) -> Settings:
        return Settings(
            ha_url=url, ha_token="t", verify_ssl=True, timeout=30,
            files_backend="none", config_dir=None, ssh_host=None, ssh_port=22,
            ssh_user=None, ssh_password=None, ssh_key_file=None,
            ssh_config_dir="/config", read_only=False, snapshots_enabled=True,
            snapshot_dir="/tmp/snaps", auto_backup_before_update=False,
            disabled_tools=set(), enabled_tools=None, transport="stdio",
            http_host="127.0.0.1", http_port=8765, http_token=None,
            builtin_mcp_url=None,
        )

    def test_ws_url_http(self) -> None:
        s = self._settings("http://ha.local:8123/")
        assert s.ws_url == "ws://ha.local:8123/api/websocket"

    def test_ws_url_https(self) -> None:
        s = self._settings("https://ha.example.com")
        assert s.ws_url == "wss://ha.example.com/api/websocket"

    def test_rest_base(self) -> None:
        s = self._settings("http://ha.local:8123/")
        assert s.rest_base == "http://ha.local:8123/api"
