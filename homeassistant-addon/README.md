# Home Assistant MCP Server add-on

This add-on runs the MCP server inside Home Assistant OS/Supervised.

Default behavior:

- MCP endpoint: `http://<home-assistant-host>:8765/mcp`
- Auth: set `http_token` in add-on options and use
  `Authorization: Bearer <token>` from your MCP client.
- Home Assistant API access: uses the Supervisor-provided token.
- YAML/file access: maps `/config` read-write and keeps MCP snapshots enabled.

Recommended first options:

```yaml
port: 8765
http_token: "choose-a-long-random-token"
read_only: false
auto_backup_before_update: true
enable_tool_search: false
pinned_tools: "get_overview,fuzzy_search,get_state,call_service"
builtin_mcp_url: ""
```

Webhook/Nabu Casa proxying is intentionally not bundled yet. This add-on is the
base layer needed before adding a webhook-proxy add-on safely.
