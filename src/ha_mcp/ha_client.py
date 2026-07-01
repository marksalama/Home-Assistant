"""Thin async client for the Home Assistant REST and WebSocket APIs."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
import websockets

from .config import Settings

logger = logging.getLogger(__name__)


class HAError(RuntimeError):
    """Raised when Home Assistant returns an error response."""


class ReadOnlyError(RuntimeError):
    """Raised when a mutating call is attempted while the server is read-only."""


# WebSocket commands that only read data. Read-only mode blocks everything
# else, so a new/unknown command is safely treated as a write by default
# (fail closed) instead of relying on a verb blacklist that new commands
# could slip through.
_READ_WS_SUFFIXES = ("/list", "/get", "/info", "/contexts")
_READ_WS_TYPES = {
    "config_entries/get",
    "frontend/get_themes",
    "energy/get_prefs",
    "lovelace/config",
    "lovelace/dashboards/list",
    "recorder/statistics_during_period",
    "recorder/list_statistic_ids",
    "recorder/get_statistics_metadata",
    "recorder/info",
    "search/related",
    "repairs/list_issues",
    "system_health/info",
    "persistent_notification/get",
    "assist_pipeline/pipeline/list",
}
# Commands that enforce read-only themselves (method-aware guards upstream).
_SELF_GUARDED_WS_TYPES = {"supervisor/api"}


def is_read_ws_command(cmd_type: str) -> bool:
    """Return True when a WebSocket command type is known to be read-only."""
    if cmd_type in _READ_WS_TYPES:
        return True
    return cmd_type.endswith(_READ_WS_SUFFIXES)


def _hint_for_status(status: int, path: str) -> str:
    if status == 401:
        return " (hint: the HA_TOKEN is invalid or expired — create a new Long-Lived Access Token)"
    if status == 404 and "/hassio" in path:
        return " (hint: Supervisor endpoints only exist on HA OS / Supervised installs)"
    if status == 404:
        return " (hint: the endpoint or entity does not exist on this Home Assistant version)"
    return ""


class HAClient:
    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self._http = httpx.AsyncClient(
            base_url=settings.rest_base,
            headers={
                "Authorization": f"Bearer {settings.ha_token}",
                "Content-Type": "application/json",
            },
            verify=settings.verify_ssl,
            timeout=settings.timeout,
            transport=httpx.AsyncHTTPTransport(retries=2, verify=settings.verify_ssl),
        )
        # Persistent WebSocket state (lazily connected, serialized by a lock).
        self._ws: Any = None
        self._ws_lock = asyncio.Lock()
        self._ws_msg_id = 0

    async def aclose(self) -> None:
        await self._http.aclose()
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None

    # ------------------------------------------------------------------ REST
    async def rest_get(self, path: str, params: dict | None = None) -> Any:
        resp = await self._http.get(path, params=params)
        return self._handle(resp)

    async def rest_get_bytes(self, path: str, params: dict | None = None) -> bytes:
        """GET raw bytes (for binary responses like camera snapshots)."""
        resp = await self._http.get(path, params=params)
        if resp.status_code >= 400:
            raise HAError(
                f"HTTP {resp.status_code} for {resp.request.url}: {resp.text}"
                + _hint_for_status(resp.status_code, path)
            )
        return resp.content

    async def rest_post(self, path: str, json_body: Any | None = None, *, write: bool = True) -> Any:
        if write:
            self._guard_write(f"POST {path}")
        resp = await self._http.post(path, json=json_body)
        return self._handle(resp)

    async def rest_delete(self, path: str) -> Any:
        self._guard_write(f"DELETE {path}")
        resp = await self._http.delete(path)
        return self._handle(resp)

    def _guard_write(self, what: str) -> None:
        if self.s.read_only:
            raise ReadOnlyError(
                f"Server is in read-only mode (HA_READ_ONLY=true); refusing to perform: {what}"
            )

    @staticmethod
    def _handle(resp: httpx.Response) -> Any:
        if resp.status_code >= 400:
            raise HAError(
                f"HTTP {resp.status_code} for {resp.request.url}: {resp.text}"
                + _hint_for_status(resp.status_code, str(resp.request.url))
            )
        if not resp.content:
            return {"ok": True}
        ctype = resp.headers.get("content-type", "")
        if "application/json" in ctype:
            return resp.json()
        return resp.text

    # ------------------------------------------------------------- WebSocket
    def _ws_connect_kwargs(self) -> dict[str, Any]:
        connect_kwargs: dict[str, Any] = {"max_size": None, "open_timeout": self.s.timeout}
        if self.s.ws_url.startswith("wss://") and not self.s.verify_ssl:
            import ssl

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            connect_kwargs["ssl"] = ctx
        return connect_kwargs

    async def _ws_open(self) -> Any:
        """Open and authenticate a new WebSocket connection."""
        ws = await websockets.connect(self.s.ws_url, **self._ws_connect_kwargs())
        try:
            await asyncio.wait_for(ws.recv(), timeout=self.s.timeout)  # auth_required
            await ws.send(json.dumps({"type": "auth", "access_token": self.s.ha_token}))
            auth = json.loads(await asyncio.wait_for(ws.recv(), timeout=self.s.timeout))
            if auth.get("type") != "auth_ok":
                raise HAError(f"WebSocket auth failed: {auth}")
        except Exception:
            await ws.close()
            raise
        return ws

    async def _ws_ensure(self) -> Any:
        if self._ws is None:
            self._ws = await self._ws_open()
            self._ws_msg_id = 0
        return self._ws

    async def _ws_reset(self) -> None:
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None

    async def ws_command(self, command: dict[str, Any]) -> Any:
        """Run one command over a persistent, authenticated WebSocket.

        The connection is opened lazily, reused across calls (one auth
        handshake instead of one per call) and transparently reopened once
        when it turns out to be stale.
        """
        cmd_type = str(command.get("type", ""))
        if cmd_type not in _SELF_GUARDED_WS_TYPES and not is_read_ws_command(cmd_type):
            self._guard_write(f"ws:{cmd_type}")

        async with self._ws_lock:
            for attempt in (1, 2):
                try:
                    return await self._ws_send(command)
                except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError) as exc:
                    await self._ws_reset()
                    if attempt == 2:
                        raise HAError(f"WebSocket connection failed: {exc}") from exc
                    logger.debug("WebSocket stale, reconnecting: %s", exc)

    async def _ws_send(self, command: dict[str, Any]) -> Any:
        ws = await self._ws_ensure()
        self._ws_msg_id += 1
        msg_id = self._ws_msg_id
        await ws.send(json.dumps({**command, "id": msg_id}))
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=self.s.timeout)
            msg = json.loads(raw)
            if msg.get("id") != msg_id:
                continue  # ignore unrelated events / stale replies
            if msg.get("type") == "result":
                if not msg.get("success", False):
                    raise HAError(f"WebSocket command failed: {msg.get('error')}")
                return msg.get("result")
