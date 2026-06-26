"""Constants for the Claude Link integration."""

DOMAIN = "claude_link"

# Runtime data key inside hass.data[DOMAIN][entry_id]
DATA = "data"

# How long without a heartbeat before we consider the bridge offline (seconds).
DEFAULT_OFFLINE_AFTER = 90
CONF_OFFLINE_AFTER = "offline_after"

SERVICE_REPORT = "report"

SIGNAL_UPDATE = "claude_link_update"

MANUFACTURER = "Claude Code"
MODEL = "MCP Bridge"
