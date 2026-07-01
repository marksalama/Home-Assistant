# Analyse & audit — Home Assistant MCP (juli 2026)

Dit document vat de grondige review en audit van de repository samen, plus de
verbeteringen die naar aanleiding daarvan zijn doorgevoerd in versie **0.4.0**.

## Samenvatting

De codebase was al goed opgezet: duidelijke modulestructuur (tools per thema),
een dunne HA-client, path-sandboxing voor bestandstoegang, confirm-vereisten
voor destructieve acties en een doordacht read-only concept. De audit vond wel
een aantal echte security-gaten, betrouwbaarheids- en performanceproblemen, en
er was ruimte voor flink wat extra functionaliteit. Alles hieronder is
opgelost/geïmplementeerd, met unit tests en CI als borging.

## 🔒 Security-bevindingen (opgelost)

| # | Ernst | Bevinding | Oplossing |
|---|-------|-----------|-----------|
| S1 | **Hoog** | De read-only guard voor WebSocket-commando's werkte met een substring-*blacklist* van werkwoorden (`create`, `update`, …). Commando's die daar niet op matchen — zoals `homeassistant/expose_entity` — konden in read-only mode **toch schrijven**. | Omgedraaid naar *fail closed*: alleen commando's die aantoonbaar read-only zijn (expliciete lijst + `/list`, `/get`, `/info` patronen) mogen door; al het onbekende wordt als write behandeld. Getest in `tests/unit/test_ws_guard.py`. |
| S2 | **Hoog** | `BearerTokenMiddleware` controleerde alleen `scope["type"] == "http"`; websocket-verbindingen gingen **zonder token** door naar de app. | Middleware controleert nu ook `websocket` scopes (sluit met code 4401) en laat alleen `lifespan` ongemoeid. Getest in `tests/unit/test_http_auth.py`. |
| S3 | **Middel** | SSH-backend gebruikte `paramiko.AutoAddPolicy` zonder host-key-persistentie: elke verbinding accepteerde élke host key (MITM-risico op wachtwoord/sleutel). | Trust-on-first-use: host keys worden bewaard in `~/.ha-mcp/known_hosts` (configureerbaar via `HA_SSH_KNOWN_HOSTS`); een *gewijzigde* key wordt daarna geweigerd. |
| S4 | Laag | Config-parsing (`int()`/`float()` op env-vars) crashte met een stacktrace, en een `HA_URL` zonder scheme gaf pas later vage fouten. | Duidelijke foutmeldingen bij ongeldige waarden; validatie van `HA_URL`-scheme, `HA_FILES_BACKEND` en `HA_TRANSPORT` bij het opstarten. |

Wat al goed was: path-sandboxing (`../`-escapes en symlink-escapes worden
geweigerd — nu ook door tests afgedekt), secrets op `chmod 600`, redactie van
secrets in `install_mcp_tools`-previews, confirm-vereisten, en het feit dat het
token nooit in tool-output belandt.

## 🐛 Bugs & betrouwbaarheid (opgelost)

1. **`get_statistics` zonder `start_time` faalde** — HA vereist een start;
   default is nu 24 uur terug. Ook periodevalidatie en meerdere statistic-ids.
2. **Nieuwe WebSocket-verbinding per commando** — elke WS-call deed een
   volledige connect + auth handshake. Er is nu één persistente verbinding met
   automatische herverbinding (1 retry bij een stale connectie) en oplopende
   message-ids. Timeouts op `recv` voorkomen hangs.
3. **Nieuwe SSH-verbinding per bestandsoperatie** — de SFTP-sessie wordt nu
   gecached en herbruikt (met health-check en lock), en de backend-instantie
   zelf wordt per proces gecached.
4. **Snapshots groeiden onbeperkt** — automatische pruning, standaard 30
   versies per bestand (`HA_SNAPSHOT_KEEP`).
5. **`run_script` valideerde de entity_id niet** (en negeerde het domein).
6. **`set_yaml_key`**: verwijdering van een key werd niet gevalideerd met
   `check_config`; nu wel. De tekst-fallback is geëxtraheerd naar het pure,
   geteste module `yaml_edit.py`.
7. **`get_overview`** rapporteerde `errors_last_hour` terwijl het het totale
   aantal log-entries was; heet nu eerlijk `error_log_entries`.
8. **REST-errors** geven nu hints bij 401 (token verlopen) en 404
   (Supervisor-endpoints op Container/Core).
9. **httpx**: 2 connect-retries voor transient netwerkfouten.

## 🏗️ Architectuur & codekwaliteit

- Nieuw module `yaml_edit.py`: pure, testbare YAML-editlogica (ruamel +
  tekst-fallback) i.p.v. 90 regels inline in de tool.
- Logging naar stderr met `HA_LOG_LEVEL` (stdout blijft schoon voor het
  MCP stdio-protocol); stille `except: pass`-plekken loggen nu op debug.
- `ruff`-configuratie in `pyproject.toml` + volledige lint-schoonmaak.
- `ha-mcp --version`, `__version__` gelijkgetrokken (0.4.0).
- **99 offline unit tests** (`tests/unit/`) voor: path-sandbox, config-
  validatie, snapshots + pruning, HTTP-auth middleware, read-only
  WS-classificatie en YAML-edits.
- Nieuw CI-workflow (`.github/workflows/ci.yml`): ruff + pytest op
  Python 3.10 en 3.13. De dev-release workflow patcht de versie nu met een
  regex i.p.v. een hardcoded string.

## ✨ Nieuwe functionaliteit (11 nieuwe tools → 159 totaal)

| Tool | Wat het doet |
|------|--------------|
| `search_related` | Alles vinden dat met een entity/device/area/automation samenhangt ("welke automations gebruiken deze sensor?") |
| `list_repair_issues` | HA's eigen Repairs-problemen (Instellingen → Reparaties) |
| `recorder_info` | Status/gezondheid van de history-database |
| `list_statistic_ids` | Beschikbare lange-termijnstatistieken vinden (met zoekfilter) |
| `get_config_entry_diagnostics` | Diagnostics-dump van een integratie downloaden |
| `clear_error_log` | Foutlog leegmaken |
| `converse` | Natuurlijke taal naar HA Assist sturen ("doe de keukenlampen aan") |
| `list_assist_pipelines` | Assist-pipelines inspecteren |
| `trigger_webhook` | Webhook-automations afvuren met payload |
| `bulk_assign_area` | Meerdere entities/devices in één keer naar een area |
| `list_device_capabilities` | Device-triggers/-conditions/-actions voor automations |

### Verbeterde bestaande tools

- `get_camera_image` levert nu **echte MCP image content** (client toont de
  foto direct); `as_base64=true` blijft beschikbaar als fallback.
- `list_entities`: extra filters `state=`, paginatie via `limit`/`offset`.
- `get_error_log`: filters `level=`, `search=`, `limit=` (scheelt veel tokens).
- `get_history`: meerdere entities in één call (komma-gescheiden).
- `get_statistics`: meerdere ids, werkende defaults.
- Discovery-proxy: correcte boolean-annotaties, strikte routing (onbekende
  tools worden geweigerd i.p.v. stilletjes uitgevoerd).

## Gebruiksvriendelijkheid

- Server-instructies (die de AI-client automatisch meekrijgt) uitgebreid met
  de nieuwe debug-, device- en voice-workflows.
- `.env.example` gedocumenteerd voor de nieuwe opties (`HA_LOG_LEVEL`,
  `HA_SNAPSHOT_KEEP`, `HA_SSH_KNOWN_HOSTS`).
- Duidelijkere foutmeldingen met vervolgstappen (token verlopen, Supervisor
  niet beschikbaar, ongeldige configuratie).

## Aanbevelingen voor later (niet in deze ronde)

1. **HACS-mutaties** (install/update via `hacs/repository/*` WS-commando's) —
   bewust read-only gelaten tot de commando-contracten per versie geverifieerd
   zijn.
2. **Event-subscripties** (bijv. `subscribe_trigger` voor "wacht tot de deur
   opent") — vergt langlopende sessies; past nu niet in het stateless model.
3. **OAuth in plaats van long-lived tokens** voor de HTTP-transport.
4. De Claude Link-integratie zou het heartbeat-interval kunnen gebruiken om
   de offline-drempel dynamisch te bepalen.
