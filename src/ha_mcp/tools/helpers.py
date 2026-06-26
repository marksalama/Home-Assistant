"""Helper entities: input_* / counter / timer / schedule storage collections."""

from __future__ import annotations

from ..app import HELPER_DOMAINS, _dump, client, mcp
from ..ha_client import HAError


def _check(helper_domain: str) -> None:
    if helper_domain not in HELPER_DOMAINS:
        raise HAError(f"Unsupported helper domain {helper_domain!r}. Allowed: {sorted(HELPER_DOMAINS)}")


@mcp.tool()
async def list_helpers(helper_domain: str) -> str:
    """List helper entities of a given domain.

    Args:
        helper_domain: One of input_boolean, input_button, input_number,
            input_text, input_select, input_datetime, counter, timer, schedule.
    """
    _check(helper_domain)
    return _dump(await client.ws_command({"type": f"{helper_domain}/list"}))


@mcp.tool()
async def create_helper(helper_domain: str, config: dict) -> str:
    """Create a helper. `config` must include at least a "name", plus domain-specific
    fields (e.g. input_number needs min/max/step)."""
    _check(helper_domain)
    return _dump(await client.ws_command({"type": f"{helper_domain}/create", **config}))


@mcp.tool()
async def update_helper(helper_domain: str, helper_id: str, config: dict) -> str:
    """Update a helper by its id (the part after the dot, e.g. for
    input_boolean.guest_mode use helper_id="guest_mode")."""
    _check(helper_domain)
    cmd = {"type": f"{helper_domain}/update", f"{helper_domain}_id": helper_id, **config}
    return _dump(await client.ws_command(cmd))


@mcp.tool()
async def delete_helper(helper_domain: str, helper_id: str) -> str:
    """Delete a helper by its id."""
    _check(helper_domain)
    cmd = {"type": f"{helper_domain}/delete", f"{helper_domain}_id": helper_id}
    return _dump(await client.ws_command(cmd))
