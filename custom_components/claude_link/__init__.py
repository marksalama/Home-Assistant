"""The Claude Link integration.

Provides monitoring entities and a `claude_link.report` service that the
Claude Code MCP bridge calls periodically. This gives a friendly, visual way to
see whether the AI connection is alive and how active it is, straight from the
Home Assistant UI.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    CONF_OFFLINE_AFTER,
    DATA,
    DEFAULT_OFFLINE_AFTER,
    DOMAIN,
    SERVICE_REPORT,
    SIGNAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.BUTTON]

REPORT_SCHEMA = vol.Schema(
    {
        vol.Optional("tool_calls"): vol.Coerce(int),
        vol.Optional("source"): cv.string,
    }
)


@dataclass
class ClaudeLinkData:
    """Runtime state shared with the entities."""

    offline_after: int = DEFAULT_OFFLINE_AFTER
    last_seen: datetime | None = None
    tool_calls: int = 0
    source: str | None = None
    extra: dict = field(default_factory=dict)

    @property
    def connected(self) -> bool:
        if self.last_seen is None:
            return False
        return (dt_util.utcnow() - self.last_seen) < timedelta(seconds=self.offline_after)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Claude Link from a config entry."""
    data = ClaudeLinkData(
        offline_after=entry.options.get(
            CONF_OFFLINE_AFTER, entry.data.get(CONF_OFFLINE_AFTER, DEFAULT_OFFLINE_AFTER)
        )
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {DATA: data}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register the report service once (covers all entries).
    if not hass.services.has_service(DOMAIN, SERVICE_REPORT):

        async def _handle_report(call: ServiceCall) -> None:
            now = dt_util.utcnow()
            for store in hass.data.get(DOMAIN, {}).values():
                d: ClaudeLinkData = store[DATA]
                d.last_seen = now
                if "tool_calls" in call.data:
                    d.tool_calls = call.data["tool_calls"]
                if "source" in call.data:
                    d.source = call.data["source"]
            async_dispatcher_send(hass, SIGNAL_UPDATE)

        hass.services.async_register(DOMAIN, SERVICE_REPORT, _handle_report, schema=REPORT_SCHEMA)

    # Periodically re-evaluate the connected state so it flips to "offline"
    # when heartbeats stop arriving.
    async def _tick(_now) -> None:
        async_dispatcher_send(hass, SIGNAL_UPDATE)

    entry.async_on_unload(
        async_track_time_interval(hass, _tick, timedelta(seconds=15))
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if not hass.data.get(DOMAIN):
            hass.services.async_remove(DOMAIN, SERVICE_REPORT)
    return unloaded
