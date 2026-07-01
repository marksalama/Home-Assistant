# Changelog

## 0.4.0 — 2026-07

Grote onderhouds- en featurerelease na een volledige code-audit. Zie
[docs/ANALYSE-EN-AUDIT.md](docs/ANALYSE-EN-AUDIT.md) voor het volledige rapport.

### Security
- Read-only mode is nu *fail closed* voor WebSocket-commando's: alleen bekende
  read-commando's mogen door; alles onbekends wordt geblokkeerd. Dit dicht een
  bypass waarbij o.a. `homeassistant/expose_entity` in read-only mode toch
  schreef.
- De HTTP/SSE Bearer-token middleware beschermt nu ook websocket-scopes
  (voorheen gingen die zonder token door).
- SSH-bestandstoegang gebruikt trust-on-first-use host keys
  (`~/.ha-mcp/known_hosts`); een gewijzigde host key wordt geweigerd.

### Nieuwe tools (148 → 159)
`search_related`, `list_repair_issues`, `recorder_info`,
`list_statistic_ids`, `get_config_entry_diagnostics`, `clear_error_log`,
`converse` (praat met Assist), `list_assist_pipelines`, `trigger_webhook`,
`bulk_assign_area`, `list_device_capabilities`.

### Verbeterd
- Persistente WebSocket-verbinding (één auth handshake i.p.v. één per call),
  met automatische herverbinding en timeouts.
- SSH/SFTP-verbinding wordt hergebruikt in plaats van per bestandsoperatie
  opnieuw opgezet.
- `get_camera_image` retourneert echte MCP image content (direct zichtbaar in
  de client); `as_base64=true` als fallback.
- `list_entities`: `state=`-filter en `limit`/`offset`-paginatie.
- `get_error_log`: filteren op `level`, `search` en `limit`.
- `get_history` en `get_statistics` ondersteunen meerdere entiteiten/ids;
  `get_statistics` werkt nu ook zonder expliciete `start_time`.
- Snapshots worden automatisch gesnoeid (`HA_SNAPSHOT_KEEP`, standaard 30).
- `set_yaml_key` valideert nu ook verwijderingen met `check_config`.
- Duidelijke configuratiefouten (ongeldige poort/URL/transport) en hints bij
  HTTP 401/404-fouten.
- Logging naar stderr via `HA_LOG_LEVEL`; `ha-mcp --version`.

### Kwaliteit
- 99 offline unit tests (path-sandbox, config, snapshots, HTTP-auth,
  read-only classificatie, YAML-edits).
- CI-workflow met ruff + pytest (Python 3.10 en 3.13); codebase lint-schoon.
- YAML-editlogica geëxtraheerd naar testbaar `yaml_edit.py` module.
