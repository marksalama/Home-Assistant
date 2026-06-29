"""Entry point: run the MCP server over stdio, SSE or Streamable HTTP."""

from __future__ import annotations

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="Home Assistant MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
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
    from .server import mcp

    mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
