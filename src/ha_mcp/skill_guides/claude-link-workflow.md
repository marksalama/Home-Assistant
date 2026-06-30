# Claude Link workflow

Claude Link is the visual Home Assistant integration for this MCP server.

- The MCP server sends a heartbeat to `claude_link.report` every 30 seconds
  after tools are used.
- Home Assistant shows connection state, heartbeat age, tool calls, transport,
  read-only mode, HTTP auth state, file-backend state, exposed tool count, and
  MCP package version.
- Use the backup button before large changes.
- Use the reset-stats button to zero the visible Home Assistant counter without
  touching the MCP process.
- If custom component code is changed live, keep the repo copy and `/config`
  copy aligned, then reload the integration or restart Home Assistant.
