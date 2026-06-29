"""Camera: take snapshots from camera entities."""

from __future__ import annotations

import base64

from ..app import _dump, client, mcp


@mcp.tool()
async def get_camera_image(entity_id: str) -> str:
    """Take a snapshot from a camera entity and return it as a base64-encoded
    JPEG image.

    Args:
        entity_id: e.g. "camera.front_door".
    """
    raw = await client.rest_get_bytes(f"/camera_proxy/{entity_id}")
    b64 = base64.b64encode(raw).decode("ascii")
    return _dump({"entity_id": entity_id, "image_base64": b64, "format": "jpeg",
                   "size_bytes": len(raw)})
