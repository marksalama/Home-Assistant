"""Unit tests for the bearer-token ASGI middleware."""

from __future__ import annotations

import asyncio

from ha_mcp.http_auth import BearerTokenMiddleware

TOKEN = "sekrit"


class DummyApp:
    def __init__(self) -> None:
        self.called = False

    async def __call__(self, scope, receive, send) -> None:
        self.called = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


def _run(scope):
    app = DummyApp()
    middleware = BearerTokenMiddleware(app, TOKEN)
    sent: list[dict] = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request"}

    asyncio.run(middleware(scope, receive, send))
    return app, sent


def _http_scope(auth: str | None):
    headers = [(b"host", b"example")]
    if auth is not None:
        headers.append((b"authorization", auth.encode()))
    return {"type": "http", "headers": headers}


def test_valid_token_passes() -> None:
    app, sent = _run(_http_scope(f"Bearer {TOKEN}"))
    assert app.called
    assert sent[0]["status"] == 200


def test_missing_token_rejected() -> None:
    app, sent = _run(_http_scope(None))
    assert not app.called
    assert sent[0]["status"] == 401


def test_wrong_token_rejected() -> None:
    app, sent = _run(_http_scope("Bearer nope"))
    assert not app.called
    assert sent[0]["status"] == 401


def test_wrong_scheme_rejected() -> None:
    app, sent = _run(_http_scope(f"Basic {TOKEN}"))
    assert not app.called
    assert sent[0]["status"] == 401


def test_websocket_without_token_closed() -> None:
    app, sent = _run({"type": "websocket", "headers": []})
    assert not app.called
    assert sent[0] == {"type": "websocket.close", "code": 4401}


def test_websocket_with_token_passes() -> None:
    scope = {"type": "websocket", "headers": [(b"authorization", f"Bearer {TOKEN}".encode())]}
    app, _sent = _run(scope)
    assert app.called


def test_lifespan_passes_without_token() -> None:
    app, _sent = _run({"type": "lifespan", "headers": []})
    assert app.called
