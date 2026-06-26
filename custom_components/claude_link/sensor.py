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

from .entity import ClaudeLinkEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        [
            ClaudeLinkLastActivity(entry, hass),
            ClaudeLinkToolCalls(entry, hass),
        ]
    )


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
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "calls"
    _attr_icon = "mdi:robot"

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_tool_calls"

    @property
    def native_value(self) -> int:
        return self._data.tool_calls
