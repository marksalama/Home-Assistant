"""Builds the default 'Claude Link' Lovelace dashboard config."""

from __future__ import annotations


def build_dashboard() -> dict:
    """Return a Lovelace dashboard config for monitoring the Claude Code link."""
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
                            {"entity": "binary_sensor.claude_link_connected", "name": "Verbonden"},
                            {"entity": "sensor.claude_link_last_activity", "name": "Laatste activiteit"},
                            {"entity": "sensor.claude_link_heartbeat_age", "name": "Heartbeat leeftijd"},
                            {"entity": "sensor.claude_link_source", "name": "Bron"},
                        ],
                    },
                    {
                        "type": "entities",
                        "title": "Activiteit",
                        "show_header_toggle": False,
                        "entities": [
                            {"entity": "sensor.claude_link_tool_calls", "name": "Acties sinds reset"},
                            {
                                "entity": "sensor.claude_link_tool_calls_per_minute",
                                "name": "Acties per minuut",
                            },
                        ],
                    },
                    {
                        "type": "entities",
                        "title": "Veiligheid",
                        "show_header_toggle": False,
                        "entities": [
                            {"entity": "binary_sensor.claude_link_read_only_mode", "name": "Alleen lezen"},
                            {"entity": "binary_sensor.claude_link_http_auth", "name": "HTTP-auth"},
                            {
                                "entity": "binary_sensor.claude_link_file_access_enabled",
                                "name": "Bestandstoegang actief",
                            },
                            {"entity": "sensor.claude_link_file_access", "name": "Bestandsbackend"},
                        ],
                    },
                    {
                        "type": "entities",
                        "title": "MCP-server",
                        "show_header_toggle": False,
                        "entities": [
                            {"entity": "sensor.claude_link_transport", "name": "Transport"},
                            {"entity": "sensor.claude_link_mcp_version", "name": "Versie"},
                            {"entity": "sensor.claude_link_exposed_tools", "name": "Zichtbare tools"},
                            {"entity": "sensor.claude_link_disabled_tools", "name": "Uitgeschakelde tools"},
                            {"entity": "sensor.claude_link_enabled_whitelist", "name": "Whitelist tools"},
                        ],
                    },
                    {
                        "type": "entities",
                        "title": "Acties",
                        "show_header_toggle": False,
                        "entities": [
                            {"entity": "button.claude_link_create_backup", "name": "Maak back-up"},
                            {
                                "entity": "button.claude_link_reset_visible_stats",
                                "name": "Reset zichtbare statistieken",
                            },
                            {
                                "entity": "button.claude_link_reload_integration",
                                "name": "Herlaad integratie",
                            },
                        ],
                    },
                    {
                        "type": "history-graph",
                        "title": "Laatste 24 uur",
                        "entities": [
                            "binary_sensor.claude_link_connected",
                            "sensor.claude_link_tool_calls",
                        ],
                        "hours_to_show": 24,
                    },
                ],
            }
        ],
    }
