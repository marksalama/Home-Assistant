"""Issue reporting helpers."""

from __future__ import annotations

from urllib.parse import quote

from ..app import _collect_overview, _dump, client, mcp

ISSUE_BASE = "https://github.com/marksalama/Home-Assistant/issues/new"


@mcp.tool()
async def report_issue(
    title: str,
    problem: str,
    include_recent_errors: bool = True,
) -> str:
    """Create a ready-to-open GitHub issue URL with useful diagnostics.

    This does not publish anything. It returns a URL the user can review first.
    """
    overview = await _collect_overview()
    recent_errors: list[str] = []
    if include_recent_errors:
        try:
            logs = await client.ws_command({"type": "system_log/list"})
            for item in (logs if isinstance(logs, list) else [])[-8:]:
                recent_errors.append(
                    f"- {item.get('level')} {item.get('name')}: {item.get('message')}"
                )
        except Exception as exc:  # noqa: BLE001
            recent_errors.append(f"- Could not read system_log/list: {exc}")

    body = "\n".join(
        [
            "## Probleem",
            problem.strip(),
            "",
            "## Omgeving",
            f"- Home Assistant: {overview.get('version')}",
            f"- Locatie: {overview.get('location_name')}",
            f"- Entiteiten: {sum(overview.get('entities_by_domain', {}).values())}",
            f"- Integraties: {overview.get('integrations')} ({overview.get('integrations_failed')} aandachtspunt(en))",
            f"- Pending updates: {overview.get('pending_updates')}",
            "",
            "## Recente foutsignalen",
            "\n".join(recent_errors) if recent_errors else "- Niet meegestuurd",
            "",
            "## Verwacht gedrag",
            "",
            "## Extra context",
        ]
    )
    url = f"{ISSUE_BASE}?title={quote(title)}&body={quote(body)}"
    return _dump(
        {
            "ok": True,
            "issue_url": url,
            "title": title,
            "body_preview": body,
            "note": "Review the issue before submitting; no data was posted automatically.",
        }
    )
