"""Camera: take snapshots from camera entities."""

from __future__ import annotations

import base64

from mcp.server.fastmcp import Image

from ..app import _dump, client, mcp


@mcp.tool()
async def get_camera_image(entity_id: str, as_base64: bool = False):
    """Take a snapshot from a camera entity.

    By default the snapshot is returned as real MCP image content so the
    client can display it directly. Set as_base64=true to get a JSON payload
    with the base64 string instead (for clients without image support).

    Args:
        entity_id: e.g. "camera.front_door".
        as_base64: Return JSON with a base64 string instead of image content.
    """
    raw = await client.rest_get_bytes(f"/camera_proxy/{entity_id}")
    if as_base64:
        b64 = base64.b64encode(raw).decode("ascii")
        return _dump({"entity_id": entity_id, "image_base64": b64, "format": "jpeg",
                      "size_bytes": len(raw)})
    return Image(data=raw, format="jpeg")
