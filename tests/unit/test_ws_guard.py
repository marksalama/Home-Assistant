"""Unit tests for the WebSocket read-only classification.

Read-only mode must fail closed: any command not known to be a read is
treated as a write.
"""

from __future__ import annotations

import pytest

from ha_mcp.ha_client import is_read_ws_command

READ_COMMANDS = [
    "config/area_registry/list",
    "config/entity_registry/list",
    "config/device_registry/list",
    "config/label_registry/list",
    "config/floor_registry/list",
    "config_entries/get",
    "system_log/list",
    "frontend/get_themes",
    "energy/get_prefs",
    "lovelace/config",
    "lovelace/dashboards/list",
    "homeassistant/expose_entity/list",
    "recorder/statistics_during_period",
    "recorder/list_statistic_ids",
    "recorder/info",
    "search/related",
    "repairs/list_issues",
    "system_health/info",
    "persistent_notification/get",
    "trace/list",
    "trace/get",
    "blueprint/list",
    "blueprint/get",
    "person/list",
    "zone/list",
    "hacs/repositories/list",
    "assist_pipeline/pipeline/list",
    "device_automation/trigger/list",
]

WRITE_COMMANDS = [
    "config/area_registry/create",
    "config/area_registry/update",
    "config/area_registry/delete",
    "config/entity_registry/update",
    "lovelace/config/save",
    "lovelace/dashboards/create",
    "blueprint/import",
    "energy/save_prefs",
    "person/create",
    "zone/delete",
    "trace/delete",
    "calendar/event/create",
    "calendar/event/update",
    "calendar/event/delete",
    # the old verb-blacklist missed this one — must stay a write
    "homeassistant/expose_entity",
    # unknown/new commands must default to write (fail closed)
    "some/new/command",
    "totally_unknown",
]


@pytest.mark.parametrize("cmd", READ_COMMANDS)
def test_read_commands_are_read(cmd: str) -> None:
    assert is_read_ws_command(cmd) is True


@pytest.mark.parametrize("cmd", WRITE_COMMANDS)
def test_write_commands_are_guarded(cmd: str) -> None:
    assert is_read_ws_command(cmd) is False
