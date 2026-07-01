"""Builds the default 'Claude Link' Lovelace dashboard config."""

from __future__ import annotations

DEFAULT_ENTITIES = {
    "connected": "binary_sensor.claude_link_connected",
    "last_activity": "sensor.claude_link_last_activity",
    "tool_calls": "sensor.claude_link_tool_calls",
    "heartbeat_age": "sensor.claude_link_heartbeat_age",
    "source": "sensor.claude_link_source",
    "calls_per_minute": "sensor.claude_link_tool_calls_per_minute",
    "read_only": "binary_sensor.claude_link_read_only_mode",
    "http_auth": "binary_sensor.claude_link_http_auth",
    "file_access_enabled": "binary_sensor.claude_link_file_access_enabled",
    "file_access": "sensor.claude_link_file_access",
    "transport": "sensor.claude_link_transport",
    "mcp_version": "sensor.claude_link_mcp_version",
    "tools_total": "sensor.claude_link_exposed_tools",
    "disabled_tools": "sensor.claude_link_disabled_tools",
    "enabled_tools": "sensor.claude_link_enabled_whitelist",
    "create_backup": "button.claude_link_create_backup",
    "reset_stats": "button.claude_link_reset_visible_stats",
    "reload_integration": "button.claude_link_reload_integration",
}


def build_dashboard(entity_ids: dict[str, str] | None = None) -> dict:
    """Return a Lovelace dashboard config for monitoring the Claude Code link."""
    e = {**DEFAULT_ENTITIES, **(entity_ids or {})}
    return {
        "title": "Claude Link",
        "views": [
            {
                "title": "Overzicht",
                "path": "overview",
                "icon": "mdi:robot-happy",
                "cards": [
                    {
                        "type": "entities",
                        "title": "Live status",
                        "show_header_toggle": False,
                        "entities": [
                            {"entity": e["connected"], "name": "Verbonden"},
                            {"entity": e["last_activity"], "name": "Laatste activiteit"},
                            {"entity": e["heartbeat_age"], "name": "Heartbeat leeftijd"},
                            {"entity": e["source"], "name": "Bron"},
                        ],
                    },
                    {
                        "type": "entities",
                        "title": "Activiteit",
                        "show_header_toggle": False,
                        "entities": [
                            {"entity": e["tool_calls"], "name": "Acties sinds reset"},
                            {"entity": e["calls_per_minute"], "name": "Acties per minuut"},
                        ],
                    },
                    {
                        "type": "entities",
                        "title": "Veiligheid",
                        "show_header_toggle": False,
                        "entities": [
                            {"entity": e["read_only"], "name": "Alleen lezen"},
                            {"entity": e["http_auth"], "name": "HTTP-auth"},
                            {"entity": e["file_access_enabled"], "name": "Bestandstoegang actief"},
                            {"entity": e["file_access"], "name": "Bestandsbackend"},
                        ],
                    },
                    {
                        "type": "entities",
                        "title": "MCP-server",
                        "show_header_toggle": False,
                        "entities": [
                            {"entity": e["transport"], "name": "Transport"},
                            {"entity": e["mcp_version"], "name": "Versie"},
                            {"entity": e["tools_total"], "name": "Zichtbare tools"},
                            {"entity": e["disabled_tools"], "name": "Uitgeschakelde tools"},
                            {"entity": e["enabled_tools"], "name": "Whitelist tools"},
                        ],
                    },
                    {
                        "type": "entities",
                        "title": "Acties",
                        "show_header_toggle": False,
                        "entities": [
                            {"entity": e["create_backup"], "name": "Maak back-up"},
                            {"entity": e["reset_stats"], "name": "Reset zichtbare statistieken"},
                            {"entity": e["reload_integration"], "name": "Herlaad integratie"},
                        ],
                    },
                    {
                        "type": "history-graph",
                        "title": "Laatste 24 uur",
                        "entities": [
                            e["connected"],
                            e["tool_calls"],
                        ],
                        "hours_to_show": 24,
                    },
                ],
            }
        ],
    }
