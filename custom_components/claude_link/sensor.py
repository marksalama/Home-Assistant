"""Diagnostic sensors for Claude Link."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA, DOMAIN
from .entity import ClaudeLinkEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    entities = [
        ClaudeLinkLastActivity(entry, hass),
        ClaudeLinkToolCalls(entry, hass),
    ]
    if data.show_advanced:
        entities.extend(
            [
                ClaudeLinkHeartbeatAge(entry, hass),
                ClaudeLinkCallsPerMinute(entry, hass),
                ClaudeLinkSource(entry, hass),
                ClaudeLinkTransport(entry, hass),
                ClaudeLinkFilesBackend(entry, hass),
                ClaudeLinkToolsTotal(entry, hass),
                ClaudeLinkDisabledTools(entry, hass),
                ClaudeLinkEnabledTools(entry, hass),
                ClaudeLinkMcpVersion(entry, hass),
            ]
        )
    async_add_entities(entities)


class ClaudeLinkLastActivity(ClaudeLinkEntity, SensorEntity):
    _attr_name = "Last activity"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_last_activity"

    @property
    def native_value(self) -> datetime | None:
        return self._data.last_seen


class ClaudeLinkToolCalls(ClaudeLinkEntity, SensorEntity):
    _attr_name = "Tool calls"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "calls"
    _attr_icon = "mdi:robot"

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_tool_calls"

    @property
    def native_value(self) -> int:
        return self._data.tool_calls

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "raw_total": self._data.raw_tool_calls,
            "reset_offset": self._data.tool_calls_offset,
        }


class ClaudeLinkHeartbeatAge(ClaudeLinkEntity, SensorEntity):
    _attr_name = "Heartbeat age"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "s"
    _attr_icon = "mdi:timer-sand"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_heartbeat_age"

    @property
    def native_value(self) -> int | None:
        return self._data.heartbeat_age


class ClaudeLinkCallsPerMinute(ClaudeLinkEntity, SensorEntity):
    _attr_name = "Tool calls per minute"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "calls/min"
    _attr_icon = "mdi:speedometer"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_calls_per_minute"

    @property
    def native_value(self) -> float | None:
        return self._data.calls_per_minute


class ClaudeLinkSource(ClaudeLinkEntity, SensorEntity):
    _attr_name = "Source"
    _attr_icon = "mdi:console"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_source"

    @property
    def native_value(self) -> str | None:
        return self._data.source


class ClaudeLinkTransport(ClaudeLinkEntity, SensorEntity):
    _attr_name = "Transport"
    _attr_icon = "mdi:transit-connection-variant"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_transport"

    @property
    def native_value(self) -> str | None:
        return self._data.transport


class ClaudeLinkFilesBackend(ClaudeLinkEntity, SensorEntity):
    _attr_name = "File access"
    _attr_icon = "mdi:file-cog"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_files_backend"

    @property
    def native_value(self) -> str | None:
        return self._data.files_backend


class ClaudeLinkToolsTotal(ClaudeLinkEntity, SensorEntity):
    _attr_name = "Exposed tools"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "tools"
    _attr_icon = "mdi:tools"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_tools_total"

    @property
    def native_value(self) -> int | None:
        return self._data.tools_total


class ClaudeLinkDisabledTools(ClaudeLinkEntity, SensorEntity):
    _attr_name = "Disabled tools"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "tools"
    _attr_icon = "mdi:toolbox"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_disabled_tools"

    @property
    def native_value(self) -> int | None:
        return self._data.disabled_tools


class ClaudeLinkEnabledTools(ClaudeLinkEntity, SensorEntity):
    _attr_name = "Enabled whitelist"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "tools"
    _attr_icon = "mdi:format-list-checks"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_enabled_tools"

    @property
    def native_value(self) -> int | None:
        return self._data.enabled_tools


class ClaudeLinkMcpVersion(ClaudeLinkEntity, SensorEntity):
    _attr_name = "MCP version"
    _attr_icon = "mdi:tag-text"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_mcp_version"

    @property
    def native_value(self) -> str | None:
        return self._data.mcp_version
