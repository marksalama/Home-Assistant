# MCP-extensieplan — Home Assistant ↔ Claude Code

> Doel: zoveel mogelijk functionaliteiten uit de twee referentie-projecten
> opnemen in onze eigen MCP-server en repo, met behoud van onze eigen
> sterke punten (visuele `claude_link`-integratie, SSH-bestandsbackend,
> setup-wizard, doctor).
>
> **Referenties**
> 1. `homeassistant-ai/ha-mcp` — *The Unofficial and Awesome Home Assistant MCP Server* (≈ 85 tools, FastMCP, HA OS add-on, OAuth, tool-search, skills)
> 2. *Home Assistant built-in MCP Server* integratie (`/api/mcp`, Assist-based, OAuth/IndieAuth, Streamable HTTP)
>
> Status: concept — 29 jun 2026

---

## 1. Samenvatting

Onze server heeft vandaag **99 tools + 5 prompts**, draait **lokaal naast Claude
Code via stdio**, en authenticeert met een **Long-Lived Access Token**. We zijn
sterk in raw-YAML-editing (met snapshots/rollback), add-onbeheer, back-ups en
de visuele `claude_link`-integratie in HA zelf.

De referenties voegen grofweg **drie lagen** toe die wij (nog) niet hebben:

| Laag | Wat het ons oplevert | Bron |
|------|----------------------|------|
| **A. Ontbrekende tools** | ≈ 25 nieuwe HA-capaciteiten (kalender, camera, todo, blueprints, groepen, HACS, automation-traces, …) | ha-mcp |
| **B. Platform/transport** | Streamable HTTP, OAuth, MCP Resources, HA OS add-on-packaging, webhook-proxy, web-UI | ha-mcp + built-in |
| **C. Agent-ondersteuning** | Tool-discovery (BM25-search), per-tool policies, Agent Skills, token-projectie, progress-reporting | ha-mcp |

Dit plan werkt in **vier fases** (P0–P3), geordend op waarde/kosten-ratio,
zodat elke fase zelfstandig leverbaar en testbaar is.

---

## 2. Huidige toestand (onze repo)

### 2.1 Architectuur

```
src/ha_mcp/
  app.py            # gedeelde FastMCP-instance + activiteits-heartbeat → claude_link
  config.py         # env-driven Settings (HA_URL, HA_TOKEN, HA_READ_ONLY, …)
  ha_client.py      # async REST + WebSocket client (één verbinding per WS-call)
  files.py          # local | ssh bestands-backend (met padbeveiliging)
  snapshots.py      # lokale snapshots voor omkeerbare YAML-wijzigingen
  server.py         # import → registreert alle tools
  setup.py          # interactieve wizard (ha-mcp-setup)
  doctor.py         # gezondheidscheck (ha-mcp-doctor)
  dashboard_template.py
  tools/
    core.py         (6)   entities, state, services, events
    automations.py  (15)  automations + scripts + scenes
    dashboards.py   (4)   Lovelace dashboards
    helpers.py      (4)   input_*, counter, timer, schedule
    registry.py     (20)  areas, floors, devices, entities, labels, persons, zones, config entries
    supervisor.py   (21)  add-ons, back-ups, logs, host, supervisor
    system.py       (11)  config, check_config, restart, reload, notifications, updates
    maintenance.py  (7)   log levels, purge, mqtt, energy, diagnose
    templates.py    (5)   render_template, history, logbook, error_log, statistics
    files_tools.py  (6)   list/read/write/delete + snapshots
    prompts.py      (5)   overview, diagnose, new_automation, edit_config, safe_update
```

- **Transport:** stdio (via `ha-mcp` entry-point in `pyproject.toml`).
- **Auth:** Long-Lived Access Token (`HA_TOKEN`).
- **Veiligheid:** `HA_READ_ONLY` (globaal), `confirm=True` op destructieve tools,
  automatische snapshots vóór YAML-wijzigingen, `HA_AUTO_BACKUP_BEFORE_UPDATE`.
- **Bestandstoegang:** `local` of `ssh` (paramiko) — géén custom component nodig.
- **Integratie in HA:** `claude_link` (HACS) — status-tegels + automatisch dashboard.
- **Setup:** één-commando wizard + `ha-mcp-doctor` gezondheidscheck.

### 2.2 Sterke punten om te behouden

1. **Visuele `claude_link`-integratie** — uniek t.o.v. ha-mcp (zij hebben alleen een add-on).
2. **SSH/local file-backend** — werkt op alle installaties zonder custom component.
3. **Setup-wizard + doctor** — lage instapdrempel.
4. **99 tools** — al ruimer dan ha-mcp's 85 in aantal; vooral supervisor/add-ons/back-ups zijn diep.
5. **Nederlandstalige docs** — onze gebruikersgroep.

---

## 3. Analyse van referentie 1 — `homeassistant-ai/ha-mcp`

### 3.1 Wat zij wel hebben en wij niet (functionele tools)

| Categorie | Hun tools | Onze status | Actie |
|-----------|-----------|-------------|-------|
| **Assist pipelines** | `ha_manage_pipeline` | ❌ ontbreekt | P1 — toevoegen |
| **Blueprints** | `ha_get_blueprint`, `ha_import_blueprint` | ❌ ontbreekt | P1 — toevoegen |
| **Kalender** | `ha_config_get/set/remove_calendar_event` | ❌ ontbreekt | P1 — toevoegen |
| **Camera** | `ha_get_camera_image` | ❌ ontbreekt | P1 — toevoegen |
| **Dashboard-screenshot** | `ha_get_dashboard_screenshot` *(beta)* | ❌ ontbreekt | P2 — toevoegen |
| **Dashboard-resources** | `ha_config_list/set/delete_dashboard_resource` | ❌ ontbreekt | P2 — toevoegen |
| **Device-verwijdering** | `ha_remove_device` | ❌ alleen `update_device` | P1 — toevoegen |
| **Entity-exposure** | `ha_get_entity_exposure` | ❌ ontbreekt | P1 — toevoegen (Assist-exposure) |
| **Entity-verwijdering** | `ha_remove_entity` | ❌ alleen `update_entity` | P1 — toevoegen |
| **Groepen** | `ha_config_list/set/remove_group` | ❌ ontbreekt | P1 — toevoegen |
| **HACS** | `ha_get_hacs_info`, `ha_manage_hacs` | ❌ ontbreekt | P2 — toevoegen |
| **Automation-traces** | `ha_get_automation_traces` | ❌ `diagnose_entity` maar geen traces | P1 — toevoegen |
| **Integratie-details** | `ha_get_integration` (options-flow) | ❌ alleen `list_config_entries` | P1 — uitbreiden |
| **Integratie enable/disable** | `ha_set_integration_enabled` | ❌ ontbreekt | P1 — toevoegen |
| **Categories** | `ha_config_get/set/remove_category` | ❌ ontbreekt | P2 — toevoegen |
| **Matter/ZHA-radio** | `ha_manage_radio` | ❌ ontbreekt | P3 — niche |
| **Systeemoverzicht** | `ha_get_overview` | ❌ alleen `list_entities` | P1 — toevoegen |
| **Fuzzy search** | `ha_search` | ⚠️ basic `search=` param | P1 — uitbreiden naar fuzzy |
| **Bulk-control** | `ha_bulk_control` | ❌ ontbreekt | P1 — toevoegen |
| **Operation-status** | `ha_get_operation_status` | ❌ ontbreekt | P2 — toevoegen |
| **Thema-beheer** | `ha_manage_theme` | ❌ ontbreekt | P3 — toevoegen |
| **Custom-tool** | `ha_manage_custom_tool` *(beta)* | ❌ ontbreekt | P3 — dynamische tools |
| **Gestructuurde YAML-edit** | `ha_config_set_yaml` *(beta)* | ⚠️ wij hebben raw file-edit | P2 — waarde toevoegen |
| **Todo-lijsten** | `ha_get_todo`, `ha_set/remove_todo_item` | ❌ ontbreekt | P1 — toevoegen |
| **MCP-tools installer** | `ha_install_mcp_tools` *(beta)* | ❌ ontbreekt | P3 — optioneel |
| **Issue reporter** | `ha_report_issue` | ❌ ontbreekt | P3 — optioneel |
| **Zone update/delete/get** | `ha_get/remove/set_zone` | ⚠️ alleen list + create | P1 — toevoegen |
| **Label get/update** | `ha_get_label` | ⚠️ alleen list/create/delete | P2 — toevoegen |
| **Person CRUD** | `ha_set/remove_person` | ⚠️ alleen list | P2 — toevoegen |

### 3.2 Platform- en framework-features die zij hebben

| Feature | Wat het doet | Onze status | Actie |
|---------|--------------|-------------|-------|
| **Streamable HTTP-transport** | Server bereikbaar over HTTP (`/mcp`) i.p.v. alleen stdio | ❌ stdio-only | P0 — toevoegen |
| **SSE-transport** | Server-Sent Events variant | ❌ | P0 — mee te leveren met HTTP |
| **OAuth (IndieAuth)** | Client-ID = base-URL van de client; gebruiker autoriseert in HA | ❌ alleen token | P2 — toevoegen |
| **Per-client WS-credentials** | In OAuth-mode per-client token voor WS-tools | ❌ | P2 — bij OAuth |
| **HA OS Add-on-packaging** | Server draait ín HA als add-on (geen aparte pc) | ❌ | P2 — add-on bouwen |
| **Webhook-proxy add-on** | Remote access via Nabu Casa zonder tunnel | ❌ | P3 — na add-on |
| **Web Settings-UI** | In-browser UI voor tool enable/disable/pin, read-only toggle | ❌ env-only | P2 — bij add-on |
| **Tool-discovery (BM25)** | `ENABLE_TOOL_SEARCH` — tools verstopt achter `ha_search_tools` | ❌ | P1 — toevoegen |
| **Per-tool enable/disable** | Individuele tools aan/uit | ❌ alleen global read-only | P1 — toevoegen |
| **Tool-security-policies** | Per-tool approval-regels met predicate-DSL (`args.domain in [...]`) | ❌ | P2 — toevoegen |
| **Agent Skills (resources)** | Bundled best-practice skills via `skill://` resources + `ha_get_skill_guide` | ❌ | P2 — toevoegen |
| **Token-projectie** | `fields=`/`attribute_keys=` op lees-tools om payload te verkleinen | ❌ | P1 — toevoegen |
| **Progress-reporting** | FastMCP `Context` voor lange tools | ❌ | P2 — toevoegen |
| **Dev-channel** | `.devN` releases op elke push naar master | ❌ | P3 — CI/CD |
| **Custom component (`ha_mcp_tools`)** | File/YAML-access zonder SSH via een HA-integratie | ❌ wij gebruiken SSH | P3 — optioneel |
| **Setup-wizard 15+ clients** | Claude Desktop/Code, Gemini, ChatGPT, Cursor, VSCode, Open WebUI… | ⚠️ alleen Claude Code | P2 — uitbreiden |

### 3.3 Wat zij niet hebben en wij wél

- **`claude_link` HACS-integratie** met visuele status-tegels + automatisch dashboard.
- **SSH-bestandsbackend** (zij vereisen een custom component voor file/YAML-access).
- **Doctor/gezondheidscheck** (`ha-mcp-doctor`).
- **Lokale snapshots** op bestandsniveau (zij hebben back-ups, niet file-snapshots).
- **Dieper add-onbeheer**: 10 add-on-tools vs hun 2 (`ha_get_addon`, `ha_manage_addon`).
- **Dieper back-upbeheer**: list/create/restore/delete vs hun `ha_manage_backup`.
- **MQTT-publish, energy-prefs, purge-database** als aparte tools.

---

## 4. Analyse van referentie 2 — HA built-in MCP Server

### 4.1 Kernarchitectuur

- Endpoint: **`/api/mcp`** in HA Core, **Streamable HTTP** (stateless).
- Auth: **OAuth (IndieAuth)** — Client-ID = base-URL van de client-app
  (`https://claude.ai`, `https://chatgpt.com`, …); Client Secret ongebruikt.
  Fallback: **Long-Lived Access Token** (wat wij al doen).
- Scope: **alleen entiteiten exposed to Assist** — beperkter dan ha-mcp.
- Tools: gebaseerd op de ingestelde LLM-API (Assist-intents).
- Resources: `homeassistant://assist/context-snapshot` (live snapshot van
  exposed entities — alleen als de LLM-API `GetLiveContext` aanbiedt).
- Prompts: ja (instructies voor de LLM over tool-gebruik).
- **Niet ondersteund:** Sampling, Notifications.

### 4.2 Wat wij ervan kunnen leren / overnemen

| Inzicht | Actie |
|---------|-------|
| Streamable HTTP is de standaard MCP-transport voor remote | P0 — onze server ook HTTP/SSE bieden |
| OAuth (IndieAuth) is de laagfrictie auth voor cloud-clients (Claude Desktop, ChatGPT) | P2 — OAuth-mode toevoegen |
| `context-snapshot` resource is handig voor inspectie/debug | P1 — vergelijkbare `homeassistant://context/overview` resource |
| Client-ID = base-URL van client is een elegant model | P2 — overnemen in onze OAuth-mode |
| `mcp-proxy` als stdio→HTTP gateway voor clients die alleen stdio ondersteunen | documenteren i.p.v. zelf bouwen |
| Exposure-scoping (alleen exposed entities) als optionele modus | P2 — `HA_ASSIST_SCOPE_ONLY` optie |

### 4.3 Positiebepaling

De built-in server is **voice-style control** van exposed entities; onze server
is **build/configure/debug** van de volledige installatie. Ze zijn complementair,
niet concurrerend. We kunnen onze server positioneren als de *configuration &
debug*-laag bovenop dezelfde HA-API's, en zelfs de built-in `/api/mcp` als
extra backend laten gebruiken (zie §6.4).

---

## 5. Gap-analyse — prioriteitenmatrix

Legenda: **W**aarde (1–5), **I**nspanning (1–5, 5 = veel), **R**atio = W−I.

### 5.1 P0 — Quick wins / fundamenteel

| # | Feature | W | I | R | Waarom |
|---|---------|---|---|---|--------|
| 0.1 | **Streamable HTTP + SSE transport** | 5 | 3 | 2 | Opent remote access & alle HTTP-clients (ChatGPT, Cursor, …); FastMCP ondersteunt het native |
| 0.2 | **`get_overview` tool** | 5 | 1 | 4 | Eén call: entiteiten-count per domein, actieve automations, errors, pending updates — immediately nuttig |
| 0.3 | **`fuzzy_search` tool** | 4 | 2 | 2 | Fuzzy entity-match (naam/area/label/device) — beter dan onze `search=` substring |
| 0.4 | **`bulk_control` tool** | 4 | 2 | 2 | Eén call bedient meerdere entiteiten/areas (efficient + token-besparend) |
| 0.5 | **Todo-lijst tools** | 4 | 2 | 2 | `get_todo`, `add_todo_item`, `update_todo_item`, `remove_todo_item` — populair bij LLM-gebruik |
| 0.6 | **Kalender tools** | 4 | 2 | 2 | `get_calendar_events`, `create/update_calendar_event`, `remove_calendar_event` |
| 0.7 | **Camera-snapshot tool** | 3 | 2 | 1 | `get_camera_image` — base64-snapshot; handig voor visuele debugging |
| 0.8 | **Blueprint tools** | 4 | 2 | 2 | `list_blueprints`, `get_blueprint`, `import_blueprint` — veelgevraagd |
| 0.9 | **Groepen tools** | 4 | 2 | 2 | `list_groups`, `create/update_group`, `remove_group` (light.group, etc.) |
| 0.10 | **Automation-traces** | 5 | 2 | 3 | `get_automation_traces`, `get_automation_trace` — debugging-kracht erbij |
| 0.11 | **Zone CRUD afronden** | 3 | 1 | 2 | `get_zone`, `update_zone`, `delete_zone` erbij |
| 0.12 | **Device/entity-verwijdering** | 3 | 1 | 2 | `remove_device`, `remove_entity` toevoegen |

### 5.2 P1 — Platform & agent-ondersteuning

| # | Feature | W | I | R | Waarom |
|---|---------|---|---|---|--------|
| 1.1 | **Tool-discovery (BM25 search)** | 5 | 3 | 2 | `ENABLE_TOOL_SEARCH` + `search_tools`/`call_read_tool`/`call_write_tool`/`call_delete_tool` proxy's — essentieel voor kleinere/local LLM's |
| 1.2 | **Per-tool enable/disable + pinning** | 4 | 2 | 2 | Fijnmaziger dan `HA_READ_ONLY`; via env `HA_DISABLED_TOOLS=a,b,c` of settings-file |
| 1.3 | **Token-projectie (`fields=`)** | 4 | 2 | 2 | Op `list_entities`, `get_state`, `list_devices`, `get_history`, … — majeure token-besparing |
| 1.4 | **MCP Resources** | 4 | 2 | 2 | `homeassistant://overview`, `homeassistant://areas`, `homeassistant://integrations` — read-only snapshots |
| 1.5 | **Integratie-details + enable/disable** | 4 | 2 | 2 | `get_integration(entry_id)` met options-flow; `set_integration_enabled` |
| 1.6 | **Entity-exposure** | 3 | 2 | 1 | `get_entity_exposure`, `set_entity_exposure` (Assist/cloud-scope) |
| 1.7 | **Dashboard-screenshot** | 3 | 3 | 0 | `get_dashboard_screenshot` (beta) — visuele feedback; afhankelijk van HA-screenshot-API |
| 1.8 | **Dashboard-resources** | 3 | 2 | 1 | `list/save/delete_dashboard_resource` (Lovelace resources/themes) |
| 1.9 | **Gestructuurde YAML-edit (`set_yaml_key`)** | 4 | 3 | 1 | Add/replace/remove top-level YAML-keys met validatie — veiliger dan raw file-edit |
| 1.10 | **Setup-wizard uitbreiden (15+ clients)** | 4 | 3 | 1 | Claude Desktop, Gemini CLI, ChatGPT, Cursor, VSCode, Open WebUI, Antigravity CLI |
| 1.11 | **Progress-reporting via `Context`** | 3 | 2 | 1 | Lange tools (back-up, install, purge) sturen progress-events |

### 5.3 P2 — Remote access, auth & packaging

| # | Feature | W | I | R | Waarom |
|---|---------|---|---|---|--------|
| 2.1 | **OAuth (IndieAuth) mode** | 4 | 4 | 0 | Client-ID = base-URL; gebruiker autoriseert in HA — laagfrictie voor cloud-clients |
| 2.2 | **HA OS Add-on-packaging** | 5 | 4 | 1 | Server draait ín HA — geen aparte pc; `repository.yaml` + `homeassistant-addon/` |
| 2.3 | **Web Settings-UI** | 4 | 3 | 1 | In-browser UI voor tool-toggle, read-only, pinned tools, feature-flags |
| 2.4 | **Tool-security-policies** | 4 | 3 | 1 | Per-tool approval-regels met predicate-DSL (`args.domain in ["light","switch"]`) |
| 2.5 | **Agent Skills (resources)** | 4 | 3 | 1 | Bundled best-practice skills via `skill://` + `get_skill_guide` tool |
| 2.6 | **HACS tools** | 3 | 3 | 0 | `get_hacs_info`, `manage_hacs` (repos, downloads, updates) |
| 2.7 | **Categories** | 2 | 2 | 0 | `get/set/remove_category` voor automations/scripts/scenes |
| 2.8 | **Person CRUD** | 2 | 2 | 0 | `create/update/remove_person` |
| 2.9 | **Label get/update** | 2 | 1 | 1 | `get_label`, `update_label` afronden |
| 2.10 | **Operation-status** | 3 | 2 | 1 | `get_operation_status` voor lange operaties |

### 5.4 P3 — Niche / optioneel

| # | Feature | W | I | R | Waarom |
|---|---------|---|---|---|--------|
| 3.1 | **Webhook-proxy add-on** | 3 | 3 | 0 | Remote via Nabu Casa — pas relevant ná add-on |
| 3.2 | **Custom component (`ha_mcp_tools`)** | 2 | 4 | −2 | File/YAML zonder SSH — wij hebben al SSH-backend |
| 3.3 | **Matter/ZHA-radio** | 2 | 3 | −1 | `manage_radio` — niche |
| 3.4 | **Thema-beheer** | 2 | 2 | 0 | `manage_theme` |
| 3.5 | **Custom-tool** | 2 | 4 | −2 | Dynamische tools toevoegen |
| 3.6 | **MCP-tools installer** | 1 | 3 | −2 | `install_mcp_tools` |
| 3.7 | **Issue reporter** | 1 | 2 | −1 | `report_issue` |
| 3.8 | **Dev-channel releases** | 2 | 2 | 0 | CI/CD pipeline |
| 3.9 | **Sampling / Notifications** | 2 | 4 | −2 | Nog niet in HA built-in; experimenteel |

---

## 6. Gedetailleerd implementatieplan per fase

### 6.1 Fase P0 — Quick wins (≈ 1–2 weken)

Doel: hoogwaardige tools toevoegen die kleine inspanning vergen en direct
merkbaar zijn. Geen architectuurwijzigingen.

#### P0.1 — `get_overview` tool

**Nieuw in `core.py`.** Eén call die samenvat:

```
{
  "version": "2026.6.x",
  "entities_by_domain": {"light": 23, "sensor": 87, ...},
  "automation_count": 42, "automation_enabled": 38,
  "script_count": 12, "scene_count": 5,
  "pending_updates": 3,
  "errors_last_hour": 7,
  "integrations": 23, "integrations_failed": 1,
  "areas": 8, "floors": 2,
  "addons_installed": 14, "addons_update_available": 2
}
```

Implementatie: combineer `client.ws_command`-calls
(`config/entity_registry/list` voor domein-counts,
`config_entries/get` voor integraties, `/services/update/list_updates` of
`/states` filtering voor updates, `error_log` voor errors). Gebruik
parallelle `asyncio.gather`.

**Onze `overview`-prompt** verwijst naar deze tool i.p.v. zelf samen te stellen.

#### P0.2 — `fuzzy_search` tool

**Nieuw in `core.py`.** Fuzzy match op entity-id, naam, area, label, device.
Strategie:
- Haal entity-registry + states + areas + labels in parallel op.
- Score op substring + eenvoudige token-overlap (geen externe dep nodig;
  optioneel `rapidfuzz` als extra dep).
- Return top-N met score, entity_id, name, area, state.

#### P0.3 — `bulk_control` tool

**Nieuw in `core.py`.**

```python
async def bulk_control(
    service: str,
    targets: list[dict],        # [{"entity_id": "..."}, {"area_id": "..."}, ...]
    data: dict | None = None,
) -> str
```

Voert `call_service` uit per target, parallel met `asyncio.gather` en
per-result error-handling. Token-besparend voor de LLM (één tool-call i.p.v. N).

#### P0.4 — Todo-lijst tools

**Nieuw bestand `tools/todo.py`.**

- `list_todo_lists()` — WS `todo/list`
- `get_todo_items(entity_id, status=None)`
- `add_todo_item(entity_id, summary, due=None, description=None)`
- `update_todo_item(entity_id, uid, summary=None, status=None, due=None)`
- `remove_todo_item(entity_id, uid)`

WS-commands: `todo/items/list`, `todo/items/add`, `todo/items/update`, `todo/items/remove`.

#### P0.5 — Kalender tools

**Nieuw bestand `tools/calendar.py`.**

- `list_calendars()` — WS `calendar/list`
- `get_calendar_events(entity_id, start, end)`
- `create_calendar_event(entity_id, summary, start, end, description=None)`
- `update_calendar_event(entity_id, uid, ...)`
- `remove_calendar_event(entity_id, uid)`

WS-commands: `calendar/events/list`, `calendar/events/create`, … (HA 2025.x+).

#### P0.6 — Camera-snapshot tool

**Toevoegen aan `tools/maintenance.py` of nieuw `tools/camera.py`.**

- `get_camera_image(entity_id, timeout=10)` — REST `GET /api/camera_proxy/{entity_id}`
  → base64-encode het PNG/JPEG. Return als data-URI of base64-string.

#### P0.7 — Blueprint tools

**Nieuw bestand `tools/blueprints.py`.**

- `list_blueprints(domain="automation"|"script")` — WS `blueprint/list`
- `get_blueprint(domain, blueprint_path)` — WS `blueprint/get`
- `import_blueprint(url)` — WS `blueprint/import`

#### P0.8 — Groepen tools

**Nieuw bestand `tools/groups.py` of toevoegen aan `registry.py`.**

- `list_groups(domain=None)` — WS `config/group/list` of filter states op `group.*`
- `create_group(name, entities, icon=None)` — `group/set` service of WS
- `update_group(group_id, entities=None, name=None)`
- `remove_group(group_id, confirm=False)`

#### P0.9 — Automation-trace tools

**Toevoegen aan `tools/maintenance.py` of nieuw `tools/traces.py`.**

- `list_automation_traces(entity_id=None, run_id=None, limit=10)` — WS `trace/list`
- `get_automation_trace(entity_id, run_id)` — WS `trace/get`
- `delete_automation_trace(entity_id, run_id)`

Koppelen aan `diagnose_entity` voor automations: trace + error-log in één call.

#### P0.10 — Zone/Device/Entity-afronding

- `get_zone(zone_id)` — WS `zone/get` (of filter uit `zone/list`)
- `update_zone(zone_id, ...)` — WS `zone/update`
- `delete_zone(zone_id, confirm=False)` — WS `zone/delete`
- `remove_device(device_id, confirm=False)` — WS `config/device_registry/remove`
- `remove_entity(entity_id, confirm=False)` — WS `config/entity_registry/remove`

Alle met `confirm=True`-patroon.

**Validatie P0:** `ha-mcp-doctor` uitbreiden met een smoke-test die elke nieuwe
tool roept met dummy-args en de response-class checkt. Minstens `pytest`-tests
met de bestaande test-patronen (zie bestaande `tests/`).

---

### 6.2 Fase P1 — Platform & agent-ondersteuning (≈ 2–3 weken)

#### P1.1 — Streamable HTTP + SSE transport

**Wijziging in `server.py` / `__main__.py`.** FastMCP ondersteunt meerdere
transports. Voeg een `--transport`-vlag toe:

```python
# ha_mcp/__main__.py
parser.add_argument("--transport", choices=["stdio","sse","http"], default=os.environ.get("HA_TRANSPORT","stdio"))
parser.add_argument("--host", default=os.environ.get("HA_HOST","127.0.0.1"))
parser.add_argument("--port", type=int, default=int(os.environ.get("HA_PORT","8765")))
```

- `stdio` (standaard, huidig gedrag — geen breuk).
- `http` → `mcp.run(transport="streamable-http", host=..., port=...)` op `/mcp`.
- `sse` → `mcp.run(transport="sse", ...)`.

Auth: Long-Lived Token via `Authorization: Bearer ...` header op de HTTP-route
(vergelijkbaar met HA's eigen `/api/mcp`). Een env `HA_HTTP_TOKEN` voor de
server-zijde; leeg = geen auth (alleen lokaal).

`mcp.example.json` uitbreiden met een HTTP-variant. Setup-wizard krijgt een
keuze stdio/HTTP.

#### P1.2 — Tool-discovery (BM25 search)

**Nieuw bestand `tools/discovery.py`.** FastMCP's BM25-search-transform kan
direct gebruikt worden. Achter `HA_ENABLE_TOOL_SEARCH=true`:

- Verberg de volledige tool-catalogus (behalve een set *pinned* tools).
- Bied 4 proxy-tools:
  - `search_tools(query, max_results=5)` — BM25 over tool-namen/descriptions; retourneert naam, parameters, annotations (`readOnlyHint`/`destructiveHint`).
  - `call_read_tool(name, args)` — voert een `readOnlyHint`-tool uit.
  - `call_write_tool(name, args)` — voert een create/update-tool uit.
  - `call_delete_tool(name, args)` — voert een delete-tool uit.
- `HA_PINNED_TOOLS=list_entities,get_overview,restart_home_assistant` — altijd zichtbaar.
- `HA_TOOL_SEARCH_MAX_RESULTS` (2–10).

Belangrijk: bestaande tools blijven direct aanroepbaar op naam; alleen de
`tools/list`-respons wordt vervangen. Documenteer dat de client zijn tool-cache
moet verversen na toggle.

#### P1.3 — Per-tool enable/disable + pinning

**Wijziging in `app.py` / `config.py`.**

- `HA_DISABLED_TOOLS=tool_a,tool_b` — comma-separated.
- `HA_ENABLED_TOOLS=...` (whitelist-modus, mutually exclusive met disabled).
- Settings-file `~/.ha-mcp/settings.json` (voor runtime-toggle via web-UI later).
- Implementatie: FastMCP-tool-decorator wrappen met een allow/deny-check vóór
  uitvoering; `tools/list` filtert de uitgeschakelde tools weg.

#### P1.4 — Token-projectie (`fields=`)

**Wijziging op lees-zware tools** (`list_entities`, `get_state`, `list_devices`,
`list_entity_registry`, `get_history`, `list_config_entries`, `list_addons`).

Voeg optionele params toe:

```python
async def list_entities(domain=None, search=None, fields=None, attribute_keys=None) -> str
```

- `fields`: whitelist van top-level keys in elk item (`["entity_id","state","name","area_id"]`).
- `attributekeys`: whitelist van state-attributes (`["brightness","color_temp"]`).
- Implementatie: post-filter op de JSON-structuur vóór `_dump`.

Token-besparing tot 80% op grote dumps — direct waardevol voor kleinere LLM's.

#### P1.5 — MCP Resources

**Nieuw bestand `tools/resources.py`** (of `src/ha_mcp/resources.py`).

FastMCP's `@mcp.resource("uri")`:

- `homeassistant://overview` — dezelfde data als `get_overview` (plain text).
- `homeassistant://areas` — area/floor-structuur.
- `homeassistant://integrations` — config-entries-samenvatting.
- `homeassistant://services` — beschikbare services per domein.
- `homeassistant://config/files` — lijst van bereikbare YAML-bestanden.

Resources zijn read-only snapshots; de LLM kan ze opvragen zonder een tool-call.
Sluit aan bij HA's eigen `homeassistant://assist/context-snapshot`-conventie.

#### P1.6 — Integratie-details + enable/disable

**Uitbreiding `registry.py`.**

- `get_integration(entry_id)` — WS `config_entries/get_entry` met options-flow-schema.
- `set_integration_enabled(entry_id, enabled)` — WS `config_entries/disable`/`enable`.

#### P1.7 — Entity-exposure

**Nieuw in `registry.py` of `tools/assist.py`.**

- `get_entity_exposure(entity_id)` — WS `homeassistant/expose_entity` of
  `entity/source` + `assist_pipeline`-exposure-list.
- `set_entity_exposure(entity_id, expose=True, assist=True, cloud=True)`.

#### P1.8 — Gestructuurde YAML-edit (`set_yaml_key`)

**Nieuw in `files_tools.py`.** Veilig add/replace/remove van top-level keys:

```python
async def set_yaml_key(
    file: str,             # "configuration.yaml" of "packages/foo.yaml"
    key: str,              # top-level key, bijv. "sensor" of "template"
    value: dict | None,    # None = verwijder de key
    confirm: bool = False,
) -> str
```

- Lees YAML → parse met `ruamel.yaml` (behoudt comments/volgorde) — nieuwe optional dep.
- Snapshot vóór wijziging (bestaand mechanisme).
- `check_config`-validatie na wijziging (optioneel, via `HA_VALIDATE_AFTER_YAML=true`).
- Werkt bovenop onze bestaande SSH/local-backend (géén custom component nodig —
  ons voordeel t.o.v. ha-mcp).

#### P1.9 — Setup-wizard uitbreiden (15+ clients)

**Wijziging in `setup.py`.** Per client een generator die het juiste config-
format schrijft:

| Client | Format | Transport |
|--------|--------|-----------|
| Claude Code | `.mcp.json` / `claude mcp add-json` | stdio of http |
| Claude Desktop | `claude_desktop_config.json` | stdio (mcp-proxy bij HTTP) |
| Gemini CLI | `.gemini/settings.json` | stdio |
| ChatGPT | remote connector (URL + OAuth) | http |
| Cursor | `~/.cursor/mcp.json` | stdio (mcp-proxy) of http |
| VSCode (Copilot) | `.vscode/mcp.json` | stdio of http |
| Open WebUI | OpenAPI/MCP-config | http |
| Antigravity CLI | `~/.gemini/antigravity-cli/mcp_config.json` | http |
| OpenCode | `opencode.json` stdio + streamable HTTP | stdio of http |

De wizard vraagt welke client(s) en genereert alle benodigde bestanden + een
stap-voor-stap printout per client.

#### P1.10 — Progress-reporting

Lange tools (`create_backup`, `install_addon`, `purge_database`, `install_update`)
rapporteren progress via FastMCP `Context`:

```python
from mcp.server.fastmcp.tools import Context
async def create_backup(name=None, ctx: Context = None) -> str:
    if ctx: await ctx.report_progress(0, 1, "Starting backup...")
    ...
    if ctx: await ctx.report_progress(1, 1, "Backup complete")
```

---

### 6.3 Fase P2 — Remote access, auth & packaging (≈ 3–5 weken)

#### P2.1 — OAuth (IndieAuth) mode

**Nieuw `src/ha_mcp/auth.py`.**

Twee modi, gestuurd door `HA_AUTH_MODE=token|oauth`:

- **token** (huidig, standaard): Long-Lived Access Token via `HA_TOKEN`.
- **oauth**: server speelt een MCP-OAuth-resource-server; HA is de
  authorization-server via `/auth/authorize` + `/auth/token`.
  - Client-ID = base-URL van de client (IndieAuth-conventie).
  - Server stuurt browser naar `HA_URL/auth/authorize?client_id=...&redirect_uri=...`.
  - Per-client Long-Lived Token wordt lokaal opgeslagen
    (`~/.ha-mcp/tokens/<client_id>.json`), persistent over herstarts.
  - WS-credentials per client (zoals ha-mcp's fix voor OAuth-mode WS-tools).

Vereist dat HA extern bereikbaar is (Nabu Casa / reverse proxy) voor cloud-
clients. Documenteer `mcp-proxy` als stdio-gateway.

#### P2.2 — HA OS Add-on-packaging

**Nieuwe mappen `homeassistant-addon/` + `repository.yaml`.**

```
homeassistant-addon/
  config.yaml          # add-on metadata (name, version, ports, options, schema)
  DOCS.md
  Dockerfile
  run.sh               # start ha-mcp met --transport=http --host=0.0.0.0
  translations/
repository.yaml        # HA add-on repository metadata
```

De add-on draait onze Python-server in een container op HA OS. De add-on
verbindt automatisch met HA Core op `homeassistant.local:8123` (supervisor-API)
— geen token-setup nodig. `HA_TOKEN` wordt via supervisor ingevuld.

Optioneel: de add-on biedt aan om de `claude_link`-integratie te installeren.

#### P2.3 — Web Settings-UI

**Nieuw `src/ha_mcp/webui/`** (lichtgewicht, bv. FastAPI of FastMCP's eigen
static-serving).

Routes:
- `GET /` — settings-formulier (tool-toggle, read-only, pinned, feature-flags).
- `POST /settings` — schrijft naar `~/.ha-mcp/settings.json` + herlaadt.
- `GET /status` — doctor-achtig overzicht.

Alleen relevant wanneer `--transport=http`. Te hosten op een aparte poort
(`HA_WEBUI_PORT`) of onder `/settings` naast `/mcp`.

#### P2.4 — Tool-security-policies

**Nieuw `src/ha_mcp/policies.py` + `~/.ha-mcp/policies.yaml`.**

Per-tool approval-regels met een predicate-DSL (geïnspireerd door PolicyLayer/ha-mcp):

```yaml
tools:
  call_service:
    require_approval:
      any:
        - args.domain in ["light", "switch", "climate"]
      none:
        - args.domain eq "notify"
  delete_config_entry:
    require_approval: true
  write_config_file:
    require_approval:
      any:
        - args.path contains "secrets"
        - args.path contains "automations.yaml"
```

- Predicates: `eq`, `in`, `regex`, `contains`, `exists`.
- Logica: `any` (OR), `none` (NOT), `all` (AND).
- Evaluatie vóór tool-uitvoering; bij `require_approval=true` → return een
  "needs approval" respons die de client moet voorleggen aan de gebruiker.
- Standaard: geen policies (alles toegestaan, zoals nu).

#### P2.5 — Agent Skills (resources)

**Nieuw `src/ha_mcp/skills/`** met bundled best-practice-skills:

- `skills/native-helpers.md` — kies de juiste helper-type i.p.v. Jinja-workarounds.
- `skills/automation-modes.md` — single/restart/queued/parallel correct gebruiken.
- `skills/safe-refactoring.md` — check_config → reload → verify workflow.
- `skills/dashboard-structure.md` — views, sections, cards per ruimte.
- `skills/template-best-practices.md` — templates spaarzaam, helpers first.

Ontsluit via FastMCP-resources `skill://native-helpers`, … én een
`get_skill_guide(skill=None, file=None)` tool (polymorf):
- geen args → list skills
- `skill=X` → list files in skill
- `skill=X&file=Y` → read content

Onze eigen toevoeging: `skills/claude-link-workflow.md` — hoe de visuele
integratie te gebruiken in combinatie met tools.

#### P2.6 — HACS tools

**Nieuw `tools/hacs.py`.** HACS exposeert een WebSocket-API (indien geïnstalleerd):

- `get_hacs_info()` — WS `hacs/repositories/list` of `/api/hacs/repositories`
- `manage_hacs(action, repository_id=None, ...)` — download/update/remove.

Valt terug op een foutmelding met installatie-instructies indien HACS afwezig is.

#### P2.7–2.10 — Afronding kleinere tools

- `categories.py`: `get/set/remove_category` (automations/scripts/scenes categoriseren).
- `persons.py`: `create/update/remove_person`.
- `labels.py` uitbreiden: `get_label`, `update_label`.
- `operation_status(operation_id)`: poll lange operaties.

---

### 6.4 Fase P3 — Niche / optioneel (geen vaste tijdlijn)

| Item | Beschrijving | Beslissing |
|------|--------------|------------|
| Webhook-proxy add-on | Remote access via Nabu Casa-webhook | pas ná P2.2 add-on |
| Custom component `ha_mcp_tools` | File/YAML zonder SSH | **waarschijnlijk overslaan** — onze SSH-backend is een sterkte |
| Matter/ZHA-radio | `manage_radio` | alleen bij gebruikersvraag |
| Thema-beheer | `manage_theme` | klein, bij gelegenheid |
| Custom-tool | dynamische tools toevoegen | experimenteel |
| MCP-tools installer | `install_mcp_tools` | overlapt met onze setup-wizard |
| Issue reporter | `report_issue` | laag prioriteit |
| Dev-channel | CI/CD met `.devN` releases | waardevol voor early-testers |
| Sampling/Notifications | experimentele MCP-features | volg HA built-in — pas als HA het ondersteunt |

#### P3.x — Synergie met HA built-in `/api/mcp`

Optioneel krachtig idee: onze server kan **naast** HA's eigen `/api/mcp`
bestaan én er gebruik van maken. Een `HA_BUILTIN_MCP_URL`-env laat onze server
de built-in `context-snapshot`-resource proxyen, zodat de LLM én
Assist-scoped control (via built-in) én volledige config/debug (via ons) heeft
in één MCP-sessie. Documenteren als "combined mode".

---

## 7. Architectuur-overwegingen

### 7.1 Conventies behouden

- Eén `HAClient`-instantie in `app.py`, tools importeren `client` + `_dump` + `mcp`.
- WebSocket-commands via `client.ws_command({...})` (stateless, één call per verbinding).
- `confirm=True`-patroon voor destructieve acties.
- `_guard_write` / read-only-handhaving in `HAClient` — geldt automatisch voor nieuwe tools.
- Bestandsbackend (`local`/`ssh`) met padbeveiliging en snapshots — hergebruik voor `set_yaml_key`.

### 7.2 Nieuwe conventies introduceren

- **Tool-annotaties**: voorzie elke tool met `readOnlyHint`/`destructiveHint`/`openWorldHint`
  via FastMCP's `annotations=`-param, zodat de discovery-proxy en security-policies ze kunnen classificeren.
- **`Context`-parameter**: lange tools accepteren `ctx: Context | None = None` voor progress.
- **Token-projectie**: standaard `fields=None` op lees-tools; documenteer in docstring.
- **Settings-file** (`~/.ha-mcp/settings.json`) als runtime-mutabele laag bovenop env-vars
  (env wint altijd, voor back-compat).

### 7.3 Afhankelijkheden

| Pakket | Doel | Fase | Optional? |
|--------|------|------|-----------|
| `ruamel.yaml` | YAML-edit met comment-behoud voor `set_yaml_key` | P1.8 | ja (`[yaml]` extra) |
| `rapidfuzz` | fuzzy entity-search | P0.2 | ja (`[search]` extra) — fallback op stdlib |
| `fastmcp` BM25-transform | tool-discovery | P1.2 | gebundeld met `mcp`-pakket |
| OAuth-libs | OAuth-mode | P2.1 | ja (`[oauth]` extra) — bv. `authlib` |
| Web-UI framework | settings-UI | P2.3 | ja (`[webui]` extra) |

Houd `pyproject.toml`-deps minimaal in de basis-installatie; alles optioneel via extras,
zoals we al doen met `[ssh]`.

### 7.4 Config-uitbreiding (`.env.example`)

Nieuwe vars om te documenteren:

```
HA_TRANSPORT=stdio           # stdio | sse | http
HA_HOST=127.0.0.1
HA_PORT=8765
HA_HTTP_TOKEN=               # bearer-token voor HTTP-mode (leeg = geen auth)

HA_AUTH_MODE=token           # token | oauth

HA_ENABLE_TOOL_SEARCH=false
HA_TOOL_SEARCH_MAX_RESULTS=5
HA_PINNED_TOOLS=
HA_DISABLED_TOOLS=
HA_ENABLED_TOOLS=

HA_VALIDATE_AFTER_YAML=true

HA_BUILTIN_MCP_URL=          # optioneel: proxy HA's eigen /api/mcp
```

---

## 8. Testen & kwaliteit

### 8.1 Teststrategie

- **Unit-tests** per tool-module met een mocked `HAClient` (patroon al aanwezig
  in `tests/`). Elke nieuwe tool-DRY krijgt minstens happy-path + error-path.
- **Contract-tests** voor WS-commands: assertie dat de command-structuur
  overeenkomt met HA's WS-API (geen echte HA nodig).
- **Integration-tests** tegen een HA-testcontainer (HA Core in Docker met
  demo-config) — één keer per PR-run.
- **Doctor-uitbreiding**: `ha-mcp-doctor` roept elke tool met veilige read-only
  args en rapporteert per tool ✅/⚠️/❌.

### 8.2 Linting / type-check

- `ruff` (al in gebruik verondersteld) — max line-length, imports.
- `mypy --strict` op `src/ha_mcp/` terloops invoeren (P1).
- Pre-commit hooks via `lefthook` of `.pre-commit-config.yaml`.

### 8.3 Documentatie

- Deze file bijwerken na elke fase.
- `README.md` tool-tabel uitbreiden naarmate tools landen.
- Per-fase `CHANGELOG.md`-entries.
- Een `docs/CLIENT-SETUP.md` met per-client instructies (P1.9-output).

---

## 9. Risico's & mitigaties

| Risico | Impact | Mitigatie |
|--------|--------|-----------|
| **Tool-explosie > 120 tools** overweldigt kleinere LLM's | hoog | P1.2 tool-discovery is de expliciete remedie; pin-lijst houdt essentials zichtbaar |
| **OAuth-complexiteit** (IndieAuth, token-persistentie, redirect-flows) | medium | P2 pas ná P1; `mcp-proxy` als fallback-documentatie; eerst token-mode blijven aanbevelen |
| **HA OS add-ononderhoud** (Docker, arch, supervisor-API-wijzigingen) | medium | bouw voort op ha-mcp's bewezen add-on-structuur; optionele deliverable |
| **Breaking changes in HA WS-API** (kalender/todo/traces zijn relatief nieuw) | medium | version-detectie in `HAClient`; graceful fallback met instructie om HA te updaten |
| **Token-besparing vs. nuttige info weggooien** (projectie) | laag | `fields=None` standaard = volledige payload; LLM kiest zelf |
| **Security-policies te streng → frustratie** | laag | standaard uit (alles toegestaan); policies zijn opt-in per tool |
| **Concurrentie/overlap met ha-mcp** | laag | wij onderscheiden ons met `claude_link` + SSH + doctor + NL docs; positie als *configuration & debug*-laag |

---

## 10. Mijlpalen & leverbaarheden

| Mijlpaal | Fase | Inhoud | Geschat |
|----------|------|--------|---------|
| **M0 — Quick wins** | P0 | 12 nieuwe tool-groepen (overview, fuzzy, bulk, todo, kalender, camera, blueprints, groepen, traces, zone/device/entity-afronding) | 1–2 wk |
| **M1 — Transport & discovery** | P1.1–1.4 | Streamable HTTP/SSE, tool-discovery, per-tool toggle, token-projectie | 2 wk |
| **M2 — Resources & integratie-detail** | P1.5–1.10 | MCP resources, integratie-detail, exposure, `set_yaml_key`, wizard 15+ clients, progress | 1–2 wk |
| **M3 — Remote & auth** | P2.1, P2.4 | OAuth-mode, tool-security-policies | 2–3 wk |
| **M4 — Add-on & UI** | P2.2, P2.3, P2.5 | HA OS add-on, web-settings-UI, agent-skills | 2–3 wk |
| **M5 — Afronding** | P2.6–2.10, P3 | HACS, categories, persons, labels, overige niche | naar behoefte |

Elke mijlpaal = eigen PR/branch met tests + docs + changelog.

---

## 11. Beslissingslog (te bevestigen)

| Vraag | Aanbeveling | Open voor |
|-------|-------------|-----------|
| Custom component `ha_mcp_tools` bouwen (naast SSH)? | **Nee** — SSH-backend is onze sterkte; vermijd dubbel onderhoud | heroverwegen bij sterke gebruikersvraag |
| BM25-search via `rapidfuzz` of stdlib? | stdlib voor P0.2; `rapidfuzz` als `[search]`-extra voor P1.2 indien FastMCP's eigen BM25 ontoereikend is | |
| Web-UI in eigen proces of ingebed in MCP-server? | ingebed achter `/settings` op dezelfde poort als `/mcp` (P2.3) | |
| OAuth self-hosted of via HA's eigen `/auth`? | via HA's `/auth` (IndieAuth) — geen eigen auth-server onderhouden | |
| Add-on als aparte repo of in deze repo? | in deze repo (`homeassistant-addon/` + `repository.yaml`), zoals ha-mcp | |
| Tool-naamconventie: `ha_*` prefix overnemen? | **Nee** — behoud onze huidige namen (`list_entities` i.p.v. `ha_search`) voor back-compat; wél aliases overwegen | |

---

## 12. Samenvattende actielijst (startvolgorde)

1. **P0.1** `get_overview` → `core.py`
2. **P0.2** `fuzzy_search` → `core.py`
3. **P0.3** `bulk_control` → `core.py`
4. **P0.4** Todo-tools → nieuw `tools/todo.py`
5. **P0.5** Kalender-tools → nieuw `tools/calendar.py`
6. **P0.6** Camera-snapshot → `tools/camera.py`
7. **P0.7** Blueprint-tools → nieuw `tools/blueprints.py`
8. **P0.8** Groepen-tools → nieuw `tools/groups.py`
9. **P0.9** Automation-traces → `tools/traces.py`
10. **P0.10** Zone/Device/Entity-afronding → `registry.py`
11. **P1.1** Streamable HTTP/SSE → `__main__.py` + `server.py`
12. **P1.2** Tool-discovery (BM25) → `tools/discovery.py`
13. **P1.3** Per-tool enable/disable → `app.py` + `config.py`
14. **P1.4** Token-projectie → lees-tools
15. **P1.5** MCP Resources → `resources.py`
16. **P1.8** `set_yaml_key` → `files_tools.py`
17. **P1.9** Setup-wizard 15+ clients → `setup.py`
18. **P2.1** OAuth-mode → `auth.py`
19. **P2.2** HA OS add-on → `homeassistant-addon/`
20. **P2.4** Tool-security-policies → `policies.py`
21. **P2.5** Agent Skills → `skills/`
22. **P2.3** Web Settings-UI → `webui/`

---

*Einde oorspronkelijke plan. Hieronder de review-resultaten en verbeterde P2-plannen.*

---

## 13. Review P0/P1 — bevindingen en verbeteringen (29 jun 2026)

### 13.1 Wat is geïmplementeerd

| Fase | Items | Status |
|------|-------|--------|
| **P0** | 12 tool-groepen: `get_overview`, `fuzzy_search`, `bulk_control`, todo (5), calendar (5), camera (1), blueprints (3), groups (4), traces (3), zone/device/entity-afronding (12) | Voltooid |
| **P1.1** | Streamable HTTP/SSE transport (`--transport http/sse/stdio`) | ✅ Voltooid |
| **P1.2** | Tool-discovery met `search_tools`/`call_read_tool`/`call_write_tool`/`call_delete_tool` | ✅ Voltooid |
| **P1.3** | Per-tool enable/disable via `HA_DISABLED_TOOLS` / `HA_ENABLED_TOOLS` | ✅ Voltooid |
| **P1.4** | Token-projectie `fields=` op `list_entities`, `attribute_keys=` op `get_state` | ✅ Voltooid |
| **P1.5** | MCP Resources: `homeassistant://overview/services/areas/integrations` | ✅ Voltooid |
| **P1.8** | `set_yaml_key` tool met YAML-validatie en fallback | ✅ Voltooid |
| **P1.9** | Setup-wizard uitgebreid naar 9 clients | ✅ Voltooid |

**Resultaat:** 99 → 141 tools (+42), 8 modules aangemaakt, 7 modules bewerkt.

### 13.2 Gevonden en opgeloste bugs (verificatie tegen echte HA 2026.6.4)

Tijdens verificatie tegen de echte HA-installatie (1547 entities, 80 integraties,
30 areas, 374 devices) werden **5 API-compatibiliteitsbugs** en **3
code-kwaliteitsissues** gevonden. Alle zijn opgelost.

| # | Bestand | Bug | Oorzaak | Oplossing |
|---|---------|-----|---------|-----------|
| 1 | `todo.py` | `todo/list` WS → `unknown_command` | Todo heeft géén WS collection API; entities via `/states`, items via `todo.*` REST services | Volledig herschreven: REST `/states` + `todo/get_items`/`add_item`/`update_item`/`remove_item` services |
| 2 | `calendar.py` | `calendar/list` WS → `unknown_command` | Calendar listing via `/states`, events via REST `/calendars/{eid}`, event CRUD via `calendar/event/*` WS | Herschreven: REST voor listing + events, WS voor create/update/delete |
| 3 | `traces.py` | `trace/list` met `limit` → `invalid_format` | `trace/list` vereist `domain` (bv. `"automation"`), accepteert geen `limit` | Parameter `domain` toegevoegd, `limit` nu post-filter op resultaten |
| 4 | `groups.py` | `config/group/list` WS → `unknown_command` | Groups hebben géén WS registry API; beheer via `group.set`/`group.remove` REST services | Herschreven: REST `/states` voor listing, `group.set`/`group.remove` services voor CRUD |
| 5 | `templates.py` | `/error_log` REST → `404 Not Found` | HA 2026.6 heeft `/api/error_log` verwijderd; error log nu via `system_log/list` WS | `get_error_log` gebruikt nu `system_log/list` WS (rijker: level, count, first_occurred) |
| 6 | `camera.py` | Binary image corruption via `resp.text` | `HAClient._handle` retourneert tekst voor non-JSON, corrupt binary data | Nieuwe `rest_get_bytes()` methode op `HAClient`; camera tool gebruikt deze |
| 7 | `registry.py` | `set_entity_exposure` verkeerde params | HA vereist `assistants` (list van `"conversation"`,`"cloud.alexa"`,`"cloud.google_assistant"`), `entity_ids` (list), `should_expose` | Parameters gecorrigeerd; `get_entity_exposure` gebruikt `homeassistant/expose_entity/list` WS |
| 8 | `discovery.py` | `_classify_tools()` niet volledig uitgevoerd | Discovery stond 7e in import-volgorde; classificatie miste 44 tools uit later geïmporteerde modules | Discovery naar laatste import verplaatst; `_classify_tools()` wordt nu vanuit `server.py` aangeroepen na alle imports |

**Verificatie-resultaat na fixes:** 13/13 tests PASS (0 FAIL) tegen echte HA.

### 13.3 Overgebleven verbeterpunten voor P2

De volgende punten zijn geïdentificeerd tijdens de review en moeten in P2 worden
aangepakt:

| # | Verbeterpunt | Prioriteit | Fase |
|---|--------------|-----------|------|
| V1 | **`get_overview` code-duplicatie met `resources.py`** — beide bevatten dezelfde logica om entity-counts/errors/areas te verzamelen. Centraliseer in een `_collect_overview()` helper in `app.py`. | medium | P2 |
| V2 | **`set_yaml_key` fallback-editor** — de string-based fallback is primitief en kan complexe YAML (lijsten, multi-line, comments) niet correct bewerken. Maak `ruamel.yaml` een aanbevolen dep (`[yaml]` extra) en documenteer dit. | hoog | P2 |
| V3 | **Todo-tools: graceful degradation** — als de `todo` integratie niet geïnstalleerd is, retourneert `list_todo_lists` leeg. Maar `get_todo_items` etc. geven een onduidelijke HAError. Voeg een pre-check toe die een duidelijke "todo integration not installed" boodschap geeft. | laag | P2 |
| V4 | **`fuzzy_search` scoring** — de huidige token-overlap scoring is basis. Overweeg `rapidfuzz` als optionele dep voor betere fuzzy matching, met stdlib fallback. | laag | P2 |
| V5 | **Token-projectie uitbreiden** — `fields=` werkt nu alleen op `list_entities` en `attribute_keys=` op `get_state`. Voeg `fields=` toe aan `list_devices`, `list_entity_registry`, `list_config_entries` voor consistente token-besparing. | medium | P2 |
| V6 | **Progress-reporting via `Context`** — nog niet geïmplementeerd. Lange tools (`create_backup`, `install_addon`, `purge_database`) zouden progress moeten rapporteren. | medium | P2 |
| V7 | **HTTP-mode auth** — `HA_HTTP_TOKEN` is gedocumenteerd in `.env.example` maar nog niet geïmplementeerd in de HTTP-transport. Voeg Bearer-token validatie toe aan de HTTP/SSE endpoint. | hoog | P2 |
| V8 | **`homeassistant/expose_entity` herhalen voor meerdere assistants** — de huidige `set_entity_exposure` ondersteunt slechts één assistant per call. Voeg een `assistants: list[str]` parameter toe voor batch-exposure. | laag | P2 |
| V9 | **Trace `entity_id` in `list_automation_traces`** — de trace entries bevatten soms geen `entity_id` veld (alleen `run_id`). De post-filter op `entity_id` kan dan misses opleveren. Verhoog robustness. | laag | P2 |
| V10 | **`get_error_log` return-formaat** — `system_log/list` retourneert een lijst met dict-items (name, message, level, source, timestamp, exception, count, first_occurred). Het bestaande `get_error_log` retourneert nu deze structured data i.p.v. raw tekst. Update de `edit_config` prompt en INSTRUCTIONS om dit te reflecteren. | medium | P2 |

### 13.4 Belangrijkste lessen voor P2-implementatie

1. **Verifieer altijd tegen een echte HA-installatie** — de HA WS/REST API
   verandert tussen versies. Commands die in de documentatie staan, bestaan
   mogelijk niet (meer) in de actuele versie. Het probe-script patroon
   (zie §13.2) moet onderdeel worden van de test-suite.

2. **Gebruik de juiste API-laag per domain** — niet alles is een WS collection:
   - **WS collections** (list/create/update/delete): areas, floors, devices,
     entities, labels, persons, zones, helpers, lovelace dashboards, blueprints
   - **REST services** (service calls): todo, group, calendar (create_event),
     light/switch/climate (call_service), notify, persistent_notification
   - **REST endpoints** (non-service): `/states`, `/calendars/{eid}`,
     `/camera_proxy/{eid}`, `/history/period`, `/logbook`
   - **WS-only**: `system_log/list`, `trace/list`, `config_entries/get`,
     `homeassistant/expose_entity`

3. **Binary responses verdienen een eigen methode** — `HAClient.rest_get_bytes()`
   is nu beschikbaar. Hergebruik voor eventuele toekomstige binary endpoints.

4. **Discovery-classificatie vereist volledige tool-registratie** — de
   `_classify_tools()` call moet ná alle tool-imports gebeuren, niet binnen
   een module die mogelijk te vroeg wordt geïmporteerd.

5. **`system_log/list` is rijker dan `/error_log`** — de nieuwe endpoint
   geeft per-error metadata (level, count, first_occurred, exception) die
   de LLM kan gebruiken voor betere diagnose.

---

## 14. Bijgewerkt P2-plan (gebaseerd op review-bevindingen)

### 14.1 P2.0 — Bug-fixes en robuustheid (vóór nieuwe features)

Voordat P2-features worden gebouwd, moeten de verbeterpunten V1–V10 uit §13.3
worden aangepakt. Dit is een korte, gerichte fase die de P0/P1-code oplost tot
productiekwaliteit.

| Item | Wat | Tijd |
|------|-----|------|
| V1 | Centraliseer `get_overview` logica in `_collect_overview()` helper | 1 u |
| V2 | Maak `ruamel.yaml` aanbevolen dep voor `set_yaml_key`; documenteer fallback-beperkingen | 2 u |
| V3 | Todo-tools: pre-check op todo-integratie met duidelijke foutmelding | 1 u |
| V5 | Token-projectie `fields=` toevoegen aan `list_devices`, `list_entity_registry`, `list_config_entries` | 2 u |
| V7 | HTTP-mode Bearer-token auth implementeren | 3 u |
| V10 | `get_error_log` return-formaat documenteren in prompts en INSTRUCTIONS | 1 u |

### 14.2 P2.1 — OAuth (IndieAuth) mode

**Onveranderd t.o.v. §6.3, met aanvullingen:**

- De `homeassistant/expose_entity` WS command vereist `assistants` als een lijst
  met waarden uit `{"conversation", "cloud.alexa", "cloud.google_assistant"}`.
  Documenteer deze waarden in de tool-docstring en in de setup-wizard.
- Test OAuth-flow tegen de echte HA-installatie vóór release — de IndieAuth-
  flow kan subtiele verschillen hebben per HA-versie.

### 14.3 P2.2 — HA OS Add-on-packaging

**Onveranderd t.o.v. §6.3, met aanvullingen:**

- De add-on moet `HA_TRANSPORT=http` gebruiken (standaard in de add-on config).
- De supervisor injecteert `HA_TOKEN` automatisch — documenteer dit.
- Test de add-on op een echte HA OS installatie (niet alleen Container/Core).
- Overweeg een `homeassistant-addon-dev/` map voor ontwikkeling (zoals ha-mcp).

### 14.4 P2.3 — Web Settings-UI

**Onveranderd t.o.v. §6.3, met aanvullingen:**

- De UI moet de huidige tool-lijst kunnen tonen (via `_tool_manager._tools`).
- Tool-toggle schrijft naar `~/.ha-mcp/settings.json` (runtime-mutabel).
- Beveilig de UI met hetzelfde `HA_HTTP_TOKEN` als de MCP-endpoint.

### 14.5 P2.4 — Tool-security-policies

**Onveranderd t.o.v. §6.3, met aanvullingen:**

- De predicate-DSL moet de `assistants` parameter van `set_entity_exposure`
  kunnen valideren (bv. `args.assistant in ["conversation"]`).
- Policies worden geëvalueerd vóór tool-uitvoering; bij afwijzing retourneer
  een structured "needs approval" response die de MCP-client kan voorleggen.

### 14.6 P2.5 — Agent Skills (resources)

**Onveranderd t.o.v. §6.3, met aanvullingen:**

- Voeg een `skills/api-reference.md` toe met een overzicht van welke HA API-laag
  (WS collection vs REST service vs REST endpoint) per domain gebruikt wordt —
  dit helpt de LLM om de juiste tool te kiezen.
- Voeg een `skills/error-diagnosis.md` toe met de nieuwe `system_log/list`
  return-formaat en hoe `list_automation_traces` + `get_automation_trace` te
  gebruiken voor automation debugging.

### 14.7 P2.6 — HACS tools

**Aanvulling:** HACS exposed WebSocket commands die per HA-versie kunnen
verschillen. Voer een probe uit tegen de echte installatie (net als §13.2)
voordat de tools worden geïmplementeerd. Verwachtte commands:
`hacs/repositories/list`, `hacs/repository/download`, `hacs/repository/update`.

### 14.8 Nieuw: P2.7 — Test-automatisering

**Nieuw item, voortkomend uit de review:**

De handmatige probe-scripts (§13.2) moeten worden geautomatiseerd:

- Maak een `tests/integration/test_ha_api.py` die alle WS/REST commands
  probeert tegen een echte HA-installatie (met `HA_URL`/`HA_TOKEN` uit .env).
- Markeer tests als `@pytest.mark.integration` zodat ze optioneel zijn in CI.
- Voeg een `ha-mcp-doctor --verify-tools` flag toe die elke read-tool aanroept
  met veilige parameters en per tool ✅/⚠️/❌ rapporteert.
- Documenteer het probe-script patroon in `CONTRIBUTING.md`.

### 14.9 Bijgewerkte P2-mijlpalen

| Mijlpaal | Fase | Inhoud | Geschat |
|----------|------|--------|---------|
| **M2a — Bug-fixes** | P2.0 | V1–V10 verbeterpunten uit review | 1–2 d |
| **M3 — Remote & auth** | P2.1, P2.4 | OAuth-mode, tool-security-policies | 2–3 wk |
| **M4 — Add-on & UI** | P2.2, P2.3, P2.5 | HA OS add-on, web-settings-UI, agent-skills | 2–3 wk |
| **M5 — Afronding** | P2.6–2.7, P3 | HACS, categories, persons, labels, test-automatisering | naar behoefte |

---

## 15. Bijgewerkte actielijst (P2 startvolgorde)

1. **P2.0/V1** Centraliseer `get_overview` logica → `app.py`
2. **P2.0/V2** `ruamel.yaml` als `[yaml]` extra in `pyproject.toml`
3. **P2.0/V3** Todo-tools graceful degradation
4. **P2.0/V5** Token-projectie op `list_devices`/`list_entity_registry`/`list_config_entries`
5. **P2.0/V7** HTTP-mode Bearer-token auth
6. **P2.0/V10** `get_error_log` return-formaat documenteren
7. **P2.7** Test-automatisering (`tests/integration/test_ha_api.py`)
8. **P2.1** OAuth-mode → `auth.py`
9. **P2.2** HA OS add-on → `homeassistant-addon/`
10. **P2.4** Tool-security-policies → `policies.py`
11. **P2.5** Agent Skills → `skills/`
12. **P2.3** Web Settings-UI → `webui/`
13. **P2.6** HACS tools → `tools/hacs.py`

---

*Einde bijgewerkt plan. P0/P1 voltooid en geverifieerd. P2 start met bug-fixes (P2.0) gevolgd door nieuwe features.*
