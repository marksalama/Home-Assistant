"""Entry point: run the MCP server over stdio, SSE or Streamable HTTP."""

from __future__ import annotations

import argparse
import os


def _normalize_transport(transport: str) -> str:
    return "streamable-http" if transport == "http" else transport


def _run_http_app(mcp, transport: str, host: str, port: int, token: str | None) -> None:
    import uvicorn

    mcp.settings.host = host
    mcp.settings.port = port
    if host not in {"127.0.0.1", "localhost", "::1"}:
        mcp.settings.transport_security = None
    if transport == "sse":
        app = mcp.sse_app()
    else:
        app = mcp.streamable_http_app()

    if token:
        from .http_auth import BearerTokenMiddleware

        app = BearerTokenMiddleware(app, token)

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=mcp.settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    server.run()


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("home-assistant-mcp")
    except PackageNotFoundError:
        return "dev"


def main() -> None:
    parser = argparse.ArgumentParser(description="Home Assistant MCP server")
    parser.add_argument(
        "--version",
        action="version",
        version=f"home-assistant-mcp {_version()}",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http", "streamable-http"],
        default=os.environ.get("HA_TRANSPORT", "stdio"),
        help="Transport to use (default: HA_TRANSPORT env or stdio)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HA_HOST", "127.0.0.1"),
        help="Bind host for HTTP/SSE (default: HA_HOST env or 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("HA_PORT", "8765")),
        help="Bind port for HTTP/SSE (default: HA_PORT env or 8765)",
    )
    args = parser.parse_args()

    # Import here so that --help style imports stay cheap and config errors
    # surface only when actually starting the server.
    from .app import settings
    from .server import mcp

    transport = _normalize_transport(args.transport)
    settings.transport = "http" if transport == "streamable-http" else transport
    settings.http_host = args.host
    settings.http_port = args.port
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        _run_http_app(mcp, transport, args.host, args.port, settings.http_token)


if __name__ == "__main__":
    main()
