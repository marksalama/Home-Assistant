"""Constants for the Claude Link integration."""

DOMAIN = "claude_link"

# Runtime data key inside hass.data[DOMAIN][entry_id]
DATA = "data"

# How long without a heartbeat before we consider the bridge offline (seconds).
DEFAULT_OFFLINE_AFTER = 90
CONF_OFFLINE_AFTER = "offline_after"
CONF_SHOW_ADVANCED = "show_advanced_entities"
DEFAULT_SHOW_ADVANCED = True

SERVICE_REPORT = "report"
SERVICE_RESET_STATS = "reset_stats"

SIGNAL_UPDATE = "claude_link_update"

MANUFACTURER = "Claude Code"
MODEL = "MCP Bridge"
