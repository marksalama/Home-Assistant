"""Builds the default 'Claude Link' Lovelace dashboard config."""

from __future__ import annotations


def build_dashboard() -> dict:
    """Return a Lovelace dashboard config (storage mode) for monitoring and
    quick control of the Claude Code link."""
    return {
        "title": "Claude Link",
        "views": [
            {
                "title": "Overzicht",
                "path": "overview",
                "icon": "mdi:robot-happy",
                "cards": [
                    {
                        "type": "markdown",
                        "content": (
                            "# 🤖 Claude Link\n"
                            "Dit dashboard is automatisch aangemaakt. Hier zie je of de "
                            "verbinding met Claude Code actief is en hoeveel acties er zijn "
                            "uitgevoerd.\n\n"
                            "Vraag Claude bijvoorbeeld: *\"zet de woonkamer in filmstand\"* of "
                            "*\"maak een automation voor de buitenverlichting bij zonsondergang\"*."
                        ),
                    },
                    {
                        "type": "entities",
                        "title": "Status",
                        "entities": [
                            {"entity": "binary_sensor.claude_link_connected", "name": "Verbonden"},
                            {"entity": "sensor.claude_link_last_activity", "name": "Laatste activiteit"},
                            {"entity": "sensor.claude_link_tool_calls", "name": "Aantal acties"},
                        ],
                    },
                    {
                        "type": "entities",
                        "title": "Snelle acties",
                        "entities": [
                            {"entity": "button.claude_link_create_backup", "name": "Maak back-up"},
                        ],
                    },
                    {
                        "type": "logbook",
                        "title": "Recente gebeurtenissen",
                        "entities": [
                            "binary_sensor.claude_link_connected",
                        ],
                        "hours_to_show": 24,
                    },
                ],
            }
        ],
    }
