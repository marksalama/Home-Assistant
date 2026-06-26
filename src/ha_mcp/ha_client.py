"""Thin async client for the Home Assistant REST and WebSocket APIs."""

from __future__ import annotations

import json
from typing import Any

import httpx
import websockets

from .config import Settings


class HAError(RuntimeError):
    """Raised when Home Assistant returns an error response."""


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
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------ REST
    async def rest_get(self, path: str, params: dict | None = None) -> Any:
        resp = await self._http.get(path, params=params)
        return self._handle(resp)

    async def rest_post(self, path: str, json_body: Any | None = None) -> Any:
        resp = await self._http.post(path, json=json_body)
        return self._handle(resp)

    async def rest_delete(self, path: str) -> Any:
        resp = await self._http.delete(path)
        return self._handle(resp)

    @staticmethod
    def _handle(resp: httpx.Response) -> Any:
        if resp.status_code >= 400:
            raise HAError(f"HTTP {resp.status_code} for {resp.request.url}: {resp.text}")
        if not resp.content:
            return {"ok": True}
        ctype = resp.headers.get("content-type", "")
        if "application/json" in ctype:
            return resp.json()
        return resp.text

    # ------------------------------------------------------------- WebSocket
    async def ws_command(self, command: dict[str, Any]) -> Any:
        """Open a short-lived authenticated WebSocket, run one command, return result.

        A fresh connection per call keeps the implementation simple and stateless,
        which is plenty for an interactive MCP workload.
        """
        connect_kwargs: dict[str, Any] = {"max_size": None, "open_timeout": self.s.timeout}
        if self.s.ws_url.startswith("wss://") and not self.s.verify_ssl:
            import ssl

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            connect_kwargs["ssl"] = ctx

        async with websockets.connect(self.s.ws_url, **connect_kwargs) as ws:
            await ws.recv()  # auth_required
            await ws.send(json.dumps({"type": "auth", "access_token": self.s.ha_token}))
            auth = json.loads(await ws.recv())
            if auth.get("type") != "auth_ok":
                raise HAError(f"WebSocket auth failed: {auth}")

            payload = {**command, "id": 1}
            await ws.send(json.dumps(payload))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") != 1:
                    continue  # ignore unrelated events
                if msg.get("type") == "result":
                    if not msg.get("success", False):
                        raise HAError(f"WebSocket command failed: {msg.get('error')}")
                    return msg.get("result")
