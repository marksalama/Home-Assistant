"""A simple, safe action button: create a full backup."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ClaudeLinkEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([ClaudeLinkBackupButton(entry, hass)])


class ClaudeLinkBackupButton(ClaudeLinkEntity, ButtonEntity):
    _attr_name = "Create backup"
    _attr_icon = "mdi:backup-restore"

    def __init__(self, entry, hass) -> None:
        super().__init__(entry, hass)
        self._attr_unique_id = f"{entry.entry_id}_create_backup"

    async def async_press(self) -> None:
        # HA OS exposes a direct Supervisor service that does not depend on a
        # selected core backup agent.
        if self.hass.services.has_service("hassio", "backup_full"):
            await self.hass.services.async_call(
                "hassio",
                "backup_full",
                {"name": "Claude Link backup", "compressed": True},
                blocking=False,
            )
        elif self.hass.services.has_service("backup", "create_automatic"):
            await self.hass.services.async_call("backup", "create_automatic", blocking=False)
        elif self.hass.services.has_service("backup", "create"):
            await self.hass.services.async_call("backup", "create", blocking=False)
        else:
            raise HomeAssistantError("No Home Assistant backup service is available.")
