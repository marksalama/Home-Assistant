#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH=/data/options.json

eval "$(
python3 - <<'PY'
import json
import shlex
from pathlib import Path

options = json.loads(Path("/data/options.json").read_text(encoding="utf-8"))

env = {
    "HA_URL": "http://supervisor/core",
    "HA_TOKEN": "${SUPERVISOR_TOKEN}",
    "HA_VERIFY_SSL": "false",
    "HA_TRANSPORT": "http",
    "HA_HOST": "0.0.0.0",
    "HA_PORT": str(options.get("port", 8765)),
    "HA_FILES_BACKEND": "local",
    "HA_CONFIG_DIR": "/config",
    "HA_READ_ONLY": "true" if options.get("read_only") else "false",
    "HA_SNAPSHOTS": "true",
    "HA_AUTO_BACKUP_BEFORE_UPDATE": "true" if options.get("auto_backup_before_update") else "false",
    "HA_ENABLE_TOOL_SEARCH": "true" if options.get("enable_tool_search") else "false",
    "HA_PINNED_TOOLS": str(options.get("pinned_tools") or ""),
}
if options.get("http_token"):
    env["HA_HTTP_TOKEN"] = str(options["http_token"])
if options.get("builtin_mcp_url"):
    env["HA_BUILTIN_MCP_URL"] = str(options["builtin_mcp_url"])

for key, value in env.items():
    if value == "${SUPERVISOR_TOKEN}":
        print(f'export {key}="${{SUPERVISOR_TOKEN}}"')
    else:
        print(f"export {key}={shlex.quote(value)}")
PY
)"

exec /opt/ha-mcp/bin/ha-mcp --transport http --host "${HA_HOST}" --port "${HA_PORT}"
