"""Connectivity binary sensor for Claude Link."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import ClaudeLinkEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([ClaudeLinkConnected(entry, hass)])


class ClaudeLinkConnected(ClaudeLinkEntity, BinarySensorEntity):
    _attr_name = "Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_unique_id = None

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_connected"

    @property
    def is_on(self) -> bool:
        return self._data.connected

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "source": self._data.source,
            "offline_after_seconds": self._data.offline_after,
        }
