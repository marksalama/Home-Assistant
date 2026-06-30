"""Connectivity binary sensor for Claude Link."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA, DOMAIN
from .entity import ClaudeLinkEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    entities = [ClaudeLinkConnected(entry, hass)]
    if data.show_advanced:
        entities.extend(
            [
                ClaudeLinkReadOnly(entry, hass),
                ClaudeLinkHttpAuth(entry, hass),
                ClaudeLinkFileAccess(entry, hass),
            ]
        )
    async_add_entities(entities)


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
            "heartbeat_age_seconds": self._data.heartbeat_age,
            "transport": self._data.transport,
            "mcp_version": self._data.mcp_version,
        }


class ClaudeLinkReadOnly(ClaudeLinkEntity, BinarySensorEntity):
    _attr_name = "Read-only mode"
    _attr_icon = "mdi:shield-lock"
    _attr_entity_category = None

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_read_only"

    @property
    def is_on(self) -> bool | None:
        return self._data.read_only


class ClaudeLinkHttpAuth(ClaudeLinkEntity, BinarySensorEntity):
    _attr_name = "HTTP auth"
    _attr_icon = "mdi:key-chain"
    _attr_entity_category = None

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_http_auth"

    @property
    def is_on(self) -> bool | None:
        return self._data.http_auth_enabled


class ClaudeLinkFileAccess(ClaudeLinkEntity, BinarySensorEntity):
    _attr_name = "File access enabled"
    _attr_icon = "mdi:file-check"
    _attr_entity_category = None

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_file_access_enabled"

    @property
    def is_on(self) -> bool | None:
        if self._data.files_backend is None:
            return None
        return self._data.files_backend != "none"
