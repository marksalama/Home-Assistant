"""HACS repository discovery."""

from __future__ import annotations

from typing import Any

from ..app import _dump, client, mcp


@mcp.tool()
async def get_hacs_info(
    search: str | None = None,
    installed_only: bool = False,
    pending_upgrade_only: bool = False,
    max_results: int = 25,
) -> str:
    """Search HACS repositories and installed custom integrations.

    This uses HACS' verified WebSocket list command. It is intentionally
    read-only; install/update/remove operations are left to the HACS UI until
    their mutation commands are probed per HA/HACS version.
    """
    repos = await client.ws_command({"type": "hacs/repositories/list"})
    result: list[dict[str, Any]] = []
    needle = search.lower() if search else None
    for repo in repos if isinstance(repos, list) else []:
        if installed_only and not repo.get("installed"):
            continue
        if pending_upgrade_only and not repo.get("pending_upgrade"):
            continue
        haystack = " ".join(
            str(repo.get(key, ""))
            for key in ("name", "full_name", "domain", "description", "category")
        ).lower()
        if needle and needle not in haystack:
            continue
        result.append(
            {
                "id": repo.get("id"),
                "name": repo.get("name"),
                "full_name": repo.get("full_name"),
                "domain": repo.get("domain"),
                "category": repo.get("category"),
                "installed": repo.get("installed"),
                "installed_version": repo.get("installed_version"),
                "available_version": repo.get("available_version"),
                "pending_upgrade": repo.get("pending_upgrade"),
                "status": repo.get("status"),
                "stars": repo.get("stars"),
                "local_path": repo.get("local_path"),
            }
        )
    result.sort(key=lambda item: (not bool(item["installed"]), item.get("name") or ""))
    max_results = max(1, min(max_results, 100))
    return _dump(
        {
            "count": len(result),
            "returned": min(len(result), max_results),
            "repositories": result[:max_results],
            "mutation_note": "Use the HACS UI for install/update/remove until mutation commands are verified.",
        }
    )
