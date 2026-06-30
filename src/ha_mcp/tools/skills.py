"""Bundled Home Assistant MCP skill guides."""

from __future__ import annotations

from importlib import resources

from ..app import _dump, mcp
from ..ha_client import HAError

SKILLS = {
    "api-reference": "Which HA API layer to use for each task.",
    "error-diagnosis": "Log, trace, and entity debugging workflow.",
    "claude-link-workflow": "How to use and maintain the visual integration.",
    "easy-setup": "Simple setup and client-install workflow.",
    "dashboard-structure": "Practical dashboard organization guidance.",
}


def _read_skill(name: str) -> str:
    if name not in SKILLS:
        raise HAError(f"Unknown skill {name!r}. Use get_skill_guide() without args to list skills.")
    return resources.files("ha_mcp.skill_guides").joinpath(f"{name}.md").read_text(encoding="utf-8")


@mcp.tool()
async def get_skill_guide(skill: str | None = None) -> str:
    """List or read bundled Home Assistant best-practice guides."""
    if skill is None:
        return _dump({"skills": SKILLS})
    return _dump({"skill": skill, "content": _read_skill(skill)})
