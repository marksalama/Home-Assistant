"""Config flow for Claude Link (UI setup, no YAML needed)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

try:
    from homeassistant.config_entries import ConfigFlowResult
except ImportError:  # pragma: no cover - compatibility with older HA versions
    from homeassistant.data_entry_flow import FlowResult as ConfigFlowResult

from .const import (
    CONF_OFFLINE_AFTER,
    CONF_SHOW_ADVANCED,
    DEFAULT_OFFLINE_AFTER,
    DEFAULT_SHOW_ADVANCED,
    DOMAIN,
)


class ClaudeLinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Single-instance, one-click setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Claude Link", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_OFFLINE_AFTER, default=DEFAULT_OFFLINE_AFTER): vol.All(
                        cv.positive_int, vol.Range(min=30, max=3600)
                    ),
                    vol.Optional(CONF_SHOW_ADVANCED, default=DEFAULT_SHOW_ADVANCED): cv.boolean,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return ClaudeLinkOptionsFlow()


class ClaudeLinkOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_OFFLINE_AFTER,
            self.config_entry.data.get(CONF_OFFLINE_AFTER, DEFAULT_OFFLINE_AFTER),
        )
        current_show_advanced = self.config_entry.options.get(
            CONF_SHOW_ADVANCED,
            self.config_entry.data.get(CONF_SHOW_ADVANCED, DEFAULT_SHOW_ADVANCED),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_OFFLINE_AFTER, default=current): vol.All(
                        cv.positive_int, vol.Range(min=30, max=3600)
                    ),
                    vol.Optional(CONF_SHOW_ADVANCED, default=current_show_advanced): cv.boolean,
                }
            ),
        )
