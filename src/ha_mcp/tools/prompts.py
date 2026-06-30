"""Reusable workflow prompts.

These appear in Claude Code as slash commands (e.g.
/mcp__home-assistant__overview) and encode the correct, safe way to perform
common Home Assistant tasks.
"""

from __future__ import annotations

from ..app import mcp


@mcp.prompt(title="Home Assistant overzicht")
def overview() -> str:
    """Give a clear, structured overview of the Home Assistant installation."""
    return (
        "Geef een helder overzicht van mijn Home Assistant. Gebruik eerst "
        "get_overview. Gebruik daarna alleen gerichte details zoals "
        "list_config_entries(fields='entry_id,domain,title,state') of "
        "list_entities(domain=..., fields='entity_id,state,friendly_name') als "
        "dat nodig is. Vat het bondig samen, geen ruwe JSON."
    )


@mcp.prompt(title="Entiteit diagnosticeren")
def diagnose(entity_id: str) -> str:
    """Debug a single entity that misbehaves."""
    return (
        f"Diagnosticeer {entity_id}. Gebruik diagnose_entity en, indien nuttig, "
        f"get_history en get_error_log. get_error_log geeft structured system_log "
        f"items met level, source, count en exception; vat alleen de relevante "
        f"regels samen. Leg in gewone taal uit wat er aan de hand lijkt en stel "
        f"een concrete oplossing voor (vraag bevestiging voor wijzigingen)."
    )


@mcp.prompt(title="Automation maken")
def new_automation(description: str) -> str:
    """Create a new automation from a plain-language description."""
    return (
        f"Maak een automation voor: {description}.\n"
        "Werkwijze: bepaal de juiste entity_ids met list_entities; stel trigger, "
        "condition en action samen; maak hem aan met upsert_automation (kies een "
        "uniek id). Laat daarna kort zien wat hij doet en hoe ik hem test met "
        "trigger_automation."
    )


@mcp.prompt(title="Veilig YAML aanpassen")
def edit_config(change: str) -> str:
    """Safely edit a YAML config file with validation and rollback awareness."""
    return (
        f"Pas mijn configuratie aan: {change}.\n"
        "Werkwijze: lees eerst het betreffende bestand met read_config_file. "
        "Gebruik set_yaml_key voor een enkele top-level YAML-key, of "
        "write_config_file voor grotere edits (de vorige versie wordt automatisch "
        "als snapshot bewaard). Draai check_config, en herlaad het domein of "
        "herstart pas als check_config slaagt. Als er iets misgaat, gebruik "
        "restore_config_file om terug te draaien."
    )


@mcp.prompt(title="Veilig updaten")
def safe_update() -> str:
    """Check for and install updates safely, with a backup first."""
    return (
        "Controleer met list_updates welke updates beschikbaar zijn. Maak eerst "
        "een back-up met create_backup. Toon mij de lijst en, na mijn akkoord, "
        "installeer de updates met install_update(confirm=true). Voor add-ons: "
        "gebruik get_addon_changelog voor control_addon(..., 'update')."
    )
