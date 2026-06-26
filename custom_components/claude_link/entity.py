"""Shared base entity for Claude Link."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from . import ClaudeLinkData
from .const import DATA, DOMAIN, MANUFACTURER, MODEL, SIGNAL_UPDATE


class ClaudeLinkEntity(Entity):
    """Base entity that groups under one device and refreshes on dispatch."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, hass) -> None:
        self._entry = entry
        self._data: ClaudeLinkData = hass.data[DOMAIN][entry.entry_id][DATA]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Claude Link",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.async_write_ha_state)
        )
