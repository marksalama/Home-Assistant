# Easy setup workflow

Use the highest-level helper first.

1. For a full guided setup, run `ha-mcp-setup`.
2. For adding one extra client later, use `get_mcp_install_options`, then
   `install_mcp_tools(client=..., write_files=true, confirm=true)`.
3. Prefer `stdio` for local clients. Prefer `http` for remote or multi-client
   access and protect it with `HA_HTTP_TOKEN`.
4. Keep `HA_READ_ONLY=true` for exploration-only sessions.
5. Install Claude Link through HACS for visual status and quick safety actions.
