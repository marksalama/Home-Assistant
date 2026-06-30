# Home Assistant API reference for this MCP server

Use the smallest API surface that fits the task.

- REST `/states`, `/services`, `/history/period`, `/logbook`, `/calendars/*`,
  and `/camera_proxy/*` are used for current state, service calls, history,
  logbook, calendar reads, and binary camera snapshots.
- WebSocket collection APIs are used for registries: areas, floors, devices,
  entities, labels, persons, zones, helpers, Lovelace dashboards, blueprints,
  config entries, traces, system log, and statistics.
- Supervisor endpoints are used only on HA OS/Supervised. This repo keeps a
  REST-first plus WebSocket `supervisor/api` fallback because some HA OS tokens
  cannot call `/api/hassio/*` directly.
- Raw YAML/file edits go through the configured file backend (`local` or `ssh`)
  and are snapshotted before writes.
