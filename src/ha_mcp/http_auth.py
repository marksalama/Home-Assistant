"""Small ASGI bearer-token guard for HTTP and SSE transports."""

from __future__ import annotations

import hmac
from collections.abc import Awaitable, Callable
from typing import Any

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


class BearerTokenMiddleware:
    """Protect an ASGI app with a single static Bearer token."""

    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]], token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin1").lower(): value.decode("latin1")
            for key, value in scope.get("headers", [])
        }
        auth = headers.get("authorization", "")
        prefix = "Bearer "
        provided = auth[len(prefix):] if auth.startswith(prefix) else ""
        if hmac.compare_digest(provided, self.token):
            await self.app(scope, receive, send)
            return

        body = b"Unauthorized: expected Authorization: Bearer <HA_HTTP_TOKEN>."
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"www-authenticate", b"Bearer"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
