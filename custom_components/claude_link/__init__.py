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
    CONF_SHOW_ADVANCED,
    DATA,
    DEFAULT_OFFLINE_AFTER,
    DEFAULT_SHOW_ADVANCED,
    DOMAIN,
    SERVICE_REPORT,
    SERVICE_RESET_STATS,
    SIGNAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.BUTTON]

REPORT_SCHEMA = vol.Schema(
    {
        vol.Optional("tool_calls"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("source"): cv.string,
        vol.Optional("transport"): cv.string,
        vol.Optional("read_only"): cv.boolean,
        vol.Optional("files_backend"): cv.string,
        vol.Optional("tools_total"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("disabled_tools"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("enabled_tools"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=0))),
        vol.Optional("http_auth_enabled"): cv.boolean,
        vol.Optional("heartbeat_interval"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("mcp_version"): cv.string,
    }
)


@dataclass
class ClaudeLinkData:
    """Runtime state shared with the entities."""

    offline_after: int = DEFAULT_OFFLINE_AFTER
    show_advanced: bool = DEFAULT_SHOW_ADVANCED
    last_seen: datetime | None = None
    previous_seen: datetime | None = None
    previous_tool_calls: int = 0
    raw_tool_calls: int = 0
    tool_calls_offset: int = 0
    tool_calls: int = 0
    source: str | None = None
    transport: str | None = None
    read_only: bool | None = None
    files_backend: str | None = None
    tools_total: int | None = None
    disabled_tools: int | None = None
    enabled_tools: int | None = None
    http_auth_enabled: bool | None = None
    heartbeat_interval: int | None = None
    mcp_version: str | None = None
    extra: dict = field(default_factory=dict)

    @property
    def connected(self) -> bool:
        if self.last_seen is None:
            return False
        return (dt_util.utcnow() - self.last_seen) < timedelta(seconds=self.offline_after)

    @property
    def heartbeat_age(self) -> int | None:
        if self.last_seen is None:
            return None
        return int((dt_util.utcnow() - self.last_seen).total_seconds())

    @property
    def calls_per_minute(self) -> float | None:
        if self.last_seen is None or self.previous_seen is None:
            return None
        elapsed = (self.last_seen - self.previous_seen).total_seconds()
        if elapsed <= 0:
            return None
        delta = max(0, self.tool_calls - self.previous_tool_calls)
        return round(delta / elapsed * 60, 2)

    def reset_stats(self) -> None:
        self.tool_calls_offset = self.raw_tool_calls
        self.previous_tool_calls = 0
        self.previous_seen = self.last_seen
        self.tool_calls = 0


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Claude Link from a config entry."""
    data = ClaudeLinkData(
        offline_after=entry.options.get(
            CONF_OFFLINE_AFTER, entry.data.get(CONF_OFFLINE_AFTER, DEFAULT_OFFLINE_AFTER)
        ),
        show_advanced=entry.options.get(
            CONF_SHOW_ADVANCED, entry.data.get(CONF_SHOW_ADVANCED, DEFAULT_SHOW_ADVANCED)
        ),
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {DATA: data}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register the report service once (covers all entries).
    if not hass.services.has_service(DOMAIN, SERVICE_REPORT):

        async def _handle_report(call: ServiceCall) -> None:
            now = dt_util.utcnow()
            for store in hass.data.get(DOMAIN, {}).values():
                d: ClaudeLinkData = store[DATA]
                d.previous_seen = d.last_seen
                d.previous_tool_calls = d.tool_calls
                d.last_seen = now
                if "tool_calls" in call.data:
                    d.raw_tool_calls = call.data["tool_calls"]
                    d.tool_calls = max(0, d.raw_tool_calls - d.tool_calls_offset)
                if "source" in call.data:
                    d.source = call.data["source"]
                if "transport" in call.data:
                    d.transport = call.data["transport"]
                if "read_only" in call.data:
                    d.read_only = call.data["read_only"]
                if "files_backend" in call.data:
                    d.files_backend = call.data["files_backend"]
                if "tools_total" in call.data:
                    d.tools_total = call.data["tools_total"]
                if "disabled_tools" in call.data:
                    d.disabled_tools = call.data["disabled_tools"]
                if "enabled_tools" in call.data:
                    d.enabled_tools = call.data["enabled_tools"]
                if "http_auth_enabled" in call.data:
                    d.http_auth_enabled = call.data["http_auth_enabled"]
                if "heartbeat_interval" in call.data:
                    d.heartbeat_interval = call.data["heartbeat_interval"]
                if "mcp_version" in call.data:
                    d.mcp_version = call.data["mcp_version"]
                d.extra = dict(call.data)
            async_dispatcher_send(hass, SIGNAL_UPDATE)

        hass.services.async_register(DOMAIN, SERVICE_REPORT, _handle_report, schema=REPORT_SCHEMA)

    if not hass.services.has_service(DOMAIN, SERVICE_RESET_STATS):

        async def _handle_reset_stats(_call: ServiceCall) -> None:
            for store in hass.data.get(DOMAIN, {}).values():
                store[DATA].reset_stats()
            async_dispatcher_send(hass, SIGNAL_UPDATE)

        hass.services.async_register(DOMAIN, SERVICE_RESET_STATS, _handle_reset_stats)

    # Periodically re-evaluate the connected state so it flips to "offline"
    # when heartbeats stop arriving.
    async def _tick(_now) -> None:
        async_dispatcher_send(hass, SIGNAL_UPDATE)

    entry.async_on_unload(
        async_track_time_interval(hass, _tick, timedelta(seconds=15))
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if not hass.data.get(DOMAIN):
            hass.services.async_remove(DOMAIN, SERVICE_REPORT)
            hass.services.async_remove(DOMAIN, SERVICE_RESET_STATS)
    return unloaded
