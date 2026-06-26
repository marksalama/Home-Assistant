"""Entry point: run the MCP server over stdio."""

from __future__ import annotations


def main() -> None:
    # Import here so that --help style imports stay cheap and config errors
    # surface only when actually starting the server.
    from .server import mcp

    mcp.run()


if __name__ == "__main__":
    main()
