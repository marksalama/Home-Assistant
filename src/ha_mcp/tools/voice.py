"""Voice / Assist: converse with Home Assistant's conversation agent and
inspect Assist pipelines."""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp


@mcp.tool()
async def converse(text: str, language: str | None = None,
                   agent_id: str | None = None) -> str:
    """Send a natural-language command or question to Home Assistant Assist
    (the built-in conversation agent), e.g. "turn on the kitchen lights".

    Useful to test what Assist understands, or to let HA's own intent engine
    handle a command. Note: this can control devices, so it is blocked in
    read-only mode.

    Args:
        text: The sentence to process.
        language: Optional language code, e.g. "nl" or "en".
        agent_id: Optional conversation agent id (default: HA's own agent).
    """
    body: dict[str, Any] = {"text": text}
    if language:
        body["language"] = language
    if agent_id:
        body["agent_id"] = agent_id
    return _dump(await client.rest_post("/conversation/process", body))


@mcp.tool()
async def list_assist_pipelines() -> str:
    """List configured Assist pipelines (speech-to-text → conversation →
    text-to-speech chains) and which one is preferred."""
    return _dump(await client.ws_command({"type": "assist_pipeline/pipeline/list"}))
