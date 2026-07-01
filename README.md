# Home Assistant ↔ Coding Agents

Geef **Coding Agents** zo veel mogelijk controle over je **Home Assistant** —
uitlezen, bedienen én aanpassen — met een visuele, gebruiksvriendelijke kant
ín Home Assistant zelf.

Dit project bestaat uit **drie onderdelen**:

| Onderdeel | Wat het doet | Waar het draait |
|-----------|--------------|-----------------|
| 🧠 **MCP-server** | 159 tools waarmee Coding agents je HA besturen, configureren, beheren en debuggen (REST + WebSocket API + ruwe YAML-bestanden) | Op je computer, naast je favoriete coding agent, of als HA OS add-on |
| 🏠 **Claude Link** (integratie) | Visuele status-tegels + automatisch dashboard in Home Assistant, installeerbaar via **HACS** | In Home Assistant |
| ✨ **Setup-wizard** | Zet alles automatisch op: verbinding testen, koppelen aan je AI-client, dashboard aanmaken | Eén commando |

> Geschikt voor **HA 2026.6+** · **HA OS / Supervised / Container / Core** · 9 AI-clients ondersteund.

Nieuw in 0.4.0: volledige security-audit (read-only mode fail-closed, HTTP-auth ook voor websockets, SSH host key-controle), persistente WebSocket/SSH-verbindingen, 11 nieuwe tools (o.a. `search_related`, `list_repair_issues`, `converse`, `bulk_assign_area`), camera-snapshots als echte afbeeldingen, unit tests + CI. Zie [CHANGELOG.md](CHANGELOG.md) en [docs/ANALYSE-EN-AUDIT.md](docs/ANALYSE-EN-AUDIT.md).

---

## 🚀 Snel starten (de makkelijke manier)

Je hoeft niet technisch te zijn. Twee stappen:

### Stap 1 — De setup-wizard draaien

**macOS / Linux** — open een terminal in deze map en plak:

```bash
bash install.sh
```

**Windows** — open PowerShell in deze map en plak:

```powershell
./install.ps1
```

De wizard:

1. vraagt het webadres van je Home Assistant (standaard `http://homeassistant.local:8123`);
2. **opent automatisch** de pagina waar je een token aanmaakt — kopieer en plak het;
3. **test** de verbinding;
4. vraagt (optioneel) je SSH-gegevens zodat Claude ook YAML-bestanden kan bewerken;
5. laat je kiezen **voor welke AI-clients** je de MCP-server wilt instellen;
6. **schrijft** `.env` + config-bestanden voor elke gekozen client;
7. **maakt** het *Claude Link*-dashboard automatisch in Home Assistant aan.

Daarna: **herstart je AI-client** en controleer of `home-assistant` verbonden is.

### Stap 2 — De visuele integratie installeren (via HACS)

1. Open in Home Assistant **HACS**.
2. Klik rechtsboven op de drie puntjes → **Aangepaste repository's** (Custom repositories).
3. Plak de URL van deze repository en kies categorie **Integratie** (Integration). Klik **Toevoegen**.
4. Zoek **Claude Link** in HACS, klik **Downloaden**, en **herstart Home Assistant**.
5. Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen**, zoek **Claude Link** en klik op **Verzenden**.

Krijg je in HACS/GitHub een **404**? Dan bestaat de repository nog niet publiek
op GitHub, of hij staat privé. Maak de repository publiek of push deze code naar
`https://github.com/marksalama/Home-Assistant`; HACS kan geen lokale map op je
computer installeren.

Je krijgt nu in Home Assistant:

- een apparaat **Claude Link** met tegels voor verbinding, activiteit, transport,
  read-only status, HTTP-auth, bestandstoegang, toolcatalogus en MCP-versie;
- knoppen voor **Maak back-up**, **Reset zichtbare statistieken** en
  **Herlaad integratie**;
- een **dashboard** in de zijbalk met live status, veiligheid, activiteit en
  snelle acties.

Klaar! 🎉

---

## 🤖 Ondersteunde AI-clients

De setup-wizard kan de MCP-server automatisch koppelen aan de volgende clients:

| Client | Transport | Config-bestand |
|--------|-----------|----------------|
| **Claude Code** (CLI) | stdio of HTTP | `.mcp.json` + `claude mcp add` |
| **Claude Desktop** | stdio (of `mcp-proxy` voor HTTP) | `claude_desktop_config.json` |
| **Gemini CLI** | stdio | `~/.gemini/settings.json` |
| **Cursor** | stdio (of `mcp-proxy` voor HTTP) | `~/.cursor/mcp.json` |
| **VSCode / GitHub Copilot** | stdio of HTTP | `.vscode/mcp.json` |
| **Open WebUI** | HTTP | Settings → MCP Servers |
| **Antigravity CLI** | stdio | `~/.gemini/antigravity-cli/mcp_config.json` |
| **OpenCode** | stdio of HTTP | `opencode.json` |
| **ChatGPT** (remote) | HTTP | Workspace settings → Apps |

> **Tip:** stdio is de standaard (server draait lokaal naast je client). HTTP-mode
> (`HA_TRANSPORT=http`) is nodig voor remote clients zoals ChatGPT of Open WebUI.

---

## 💬 Wat kun je nu tegen Claude zeggen?

- "Geef me een overzicht van mijn hele installatie."
- "Zet alle lampen in de woonkamer op 30%."
- "Maak een scene 'filmavond' met gedimd licht en de tv aan."
- "Schrijf een automation die de buitenverlichting bij zonsondergang aanzet."
- "Debug waarom mijn ochtend-automation niet liep — laat de trace zien."
- "Laat de error log zien en los de waarschuwingen op."
- "Voeg een helper `vakantiemodus` toe en gebruik die in een automation."
- "Open `configuration.yaml`, voeg een template-sensor toe, valideer en herstart."
- "Maak een back-up en update de Mosquitto add-on."
- "Maak een nieuw dashboard met een kaart per kamer."
- "Welke entiteiten zijn exposed aan Assist?"
- "Importeer een blueprint van de community forum."
- "Voeg een afspraak toe aan mijn agenda."
- "Zet alle lichten uit in de woonkamer, keuken en hal in één keer."
- "Installeer de MCP-koppeling ook voor VSCode."
- "Zet het Home Assistant thema op default dark."
- "Maak een GitHub issue met de relevante foutlogs."

### Kant-en-klare opdrachten (slash-commando's)

De koppeling levert een paar veilige, uitgewerkte workflows die je in Claude
Code als commando kunt typen — handig als je niet wilt nadenken over de juiste
stappen:

| Commando | Wat het doet |
|----------|--------------|
| `/mcp__home-assistant__overview` | Een helder overzicht van je hele installatie |
| `/mcp__home-assistant__diagnose` | Eén entiteit doormeten en problemen verklaren |
| `/mcp__home-assistant__new_automation` | Een automation maken vanuit een beschrijving |
| `/mcp__home-assistant__edit_config` | Veilig YAML aanpassen (met validatie + rollback) |
| `/mcp__home-assistant__safe_update` | Updates checken en installeren mét back-up |

> Claude krijgt bij het verbinden automatisch instructies mee over de juiste,
> efficiënte manier van werken (filteren i.p.v. alles ophalen, eerst
> `check_config`, snapshots/back-ups, control vs. config). Je hoeft dus niet
> precies te weten welke tool wanneer nodig is — vraag gewoon wat je wilt.

### Controleren of alles werkt

Twijfel je of de koppeling goed staat? Draai het controle-commando — het test
de verbinding, de WebSocket, bestandstoegang, de integratie en je
bestandsrechten, en geeft per onderdeel een ✅/⚠️/❌ met tips:

```bash
# Windows PowerShell
.\.venv\Scripts\ha-mcp-doctor.exe

# macOS / Linux
./.venv/bin/ha-mcp-doctor
```

Wil je ook de veilige read-tools tegen je echte HA API controleren, gebruik dan:

```bash
.\.venv\Scripts\ha-mcp-doctor.exe --verify-tools
# macOS / Linux:
./.venv/bin/ha-mcp-doctor --verify-tools
```

---

## 🧰 Wat de MCP-server allemaal kan (159 tools)

| Categorie | Tools |
|-----------|-------|
| **States & besturing** | `list_entities` (met `fields=`, `state=`, `limit`/`offset`), `get_state` (met `attribute_keys=`), `set_state`, `call_service`, `fire_event`, `list_services`, `bulk_control`, `trigger_webhook` |
| **Overzicht & zoeken** | `get_overview`, `fuzzy_search` (fuzzy match op naam/area/label) |
| **Automations** | `list/get/upsert/delete/trigger_automation` |
| **Scripts** | `list/get/upsert/delete/run_script` |
| **Scenes** | `list/get/upsert/delete/activate_scene` |
| **Blueprints** | `list_blueprints`, `get_blueprint`, `import_blueprint` |
| **Automation-traces** | `list_automation_traces`, `get_automation_trace`, `delete_automation_trace` |
| **Todo-lijsten** | `list_todo_lists`, `get/add/update/remove_todo_item` |
| **Kalender** | `list_calendars`, `get/create/update/remove_calendar_event` |
| **Camera** | `get_camera_image` (echte MCP-afbeelding; `as_base64=true` als fallback) |
| **Dashboards** | `list/get/save/create_dashboard` |
| **Helpers** | `list/create/update/delete_helper` (input_\*, counter, timer, schedule) |
| **Groepen** | `list/create/update/remove_group` |
| **Areas & floors** | `list/create/update/delete_area`, `list/create/update/delete_floor` |
| **Devices & entities** | `list/update/remove_device`, `list_device_capabilities` (device-triggers/-conditions/-actions), `list_entity_registry` (met `fields=`), `update/remove_entity`, `bulk_assign_area`, `get/set_entity_exposure` |
| **Labels, personen, zones** | `list/get/create/update/delete_label`, `list/create/update/remove_person`, `list/get/create/update/delete_zone` |
| **Integraties** | `list_config_entries` (met `fields=`), `reload/delete_config_entry` |
| **Add-on-beheer** (HA OS) | `list_addons`, `list_available_addons`, `get_addon_info/stats/changelog/logs`, `install_addon`, `uninstall_addon`, `set_addon_options`, `control_addon` (start/stop/restart/update/rebuild) |
| **Back-ups & rollback** | `list/create/restore/delete_backup`, `list_file_snapshots`, `restore_config_file` |
| **Debug & onderhoud** | `get_core/supervisor/host_logs`, `get_error_log` (met `level=`, `search=`, `limit=`), `clear_error_log`, `set_log_level`, `set_default_log_level`, `diagnose_entity`, `search_related`, `list_repair_issues`, `recorder_info`, `get_config_entry_diagnostics`, `purge_database`, `system_health` |
| **Systeem** | `get_config`, `check_config`, `restart_home_assistant`, `reload_domain`, `update_supervisor`, `reboot_host` |
| **Thema's** | `list_themes`, `manage_theme` (`list`, `set`, `reload`) |
| **HACS** | `get_hacs_info` (veilig zoeken/lezen van HACS repositories) |
| **Setup & support** | `get_mcp_install_options`, `install_mcp_tools`, `report_issue`, `get_skill_guide` |
| **MQTT & energie** | `mqtt_publish`, `get_energy_prefs`, `save_energy_prefs` |
| **Voice / Assist** | `converse` (natuurlijke taal naar Assist), `list_assist_pipelines` |
| **Meldingen & updates** | `list/create/dismiss_notification`, `notify`, `list_updates`, `install_update` (met back-up) |
| **Templates & data** | `render_template`, `get_history` (meerdere entities), `get_logbook`, `get_statistics`, `list_statistic_ids` |
| **YAML-bestanden** | `list/read/write/delete_config_file`, `set_yaml_key` (gestructureerde edit met validatie), `restore_config_file` (met snapshots) |
| **Discovery & MCP** | `search_tools`, `call_read_tool`, `call_write_tool`, `call_delete_tool` |

### MCP Resources (read-only snapshots)

Naast tools biedt de server ook **MCP Resources** die je AI-client kan opvragen
zonder een tool-call — handig voor context:

| URI | Inhoud |
|-----|--------|
| `homeassistant://overview` | Installatie-overzicht (versie, entity-counts, errors, areas) |
| `homeassistant://services` | Alle beschikbare services per domein |
| `homeassistant://areas` | Alle areas en floors |
| `homeassistant://integrations` | Alle config entries met hun state |
| `homeassistant://assist/context-snapshot` | Proxy naar HA's built-in MCP Assist context snapshot wanneer `HA_BUILTIN_MCP_URL` is ingesteld |
| `skill://api-reference` e.a. | Bundled best-practice guides voor API-keuze, setup, diagnose, dashboards en Claude Link |

---

## 🔎 Tool-discovery (voor kleinere / lokale LLM's)

Met 159 tools kan de tool-catalogus kleinere modellen (Claude Haiku, Gemini,
ChatGPT, lokale Ollama-modellen) overweldigen. Zet **search-based discovery**
aan om alleen de benodigde tools in context te laden:

```bash
HA_ENABLE_TOOL_SEARCH=true
```

De volledige catalogus wordt dan vervangen door vier entry-points:

| Tool | Doel |
|------|------|
| `search_tools` | Zoek tools op trefwoord (token-overlap scoring) |
| `call_read_tool` | Voer een alleen-lezen tool uit |
| `call_write_tool` | Voer een schrijf-tool uit (create/update) |
| `call_delete_tool` | Voer een verwijder-tool uit |

Houd essentiële tools altijd zichtbaar met `HA_PINNED_TOOLS=list_entities,get_overview,get_state,call_service`.

> **Belangrijk:** na het wijzigen van deze instelling moet je AI-client zijn
> tool-lijst vernieuwen (opnieuw verbinden of de MCP-server herstarten).

---

## 🛟 Fool-proof: niets gaat onomkeerbaar stuk

Veiligheid zit standaard ingebouwd, zodat je rustig kunt experimenteren:

- **Automatische snapshots** — elke keer dat Claude een YAML-bestand wijzigt of
  verwijdert, wordt de vorige versie lokaal bewaard. Eén opdracht (*"draai die
  wijziging terug"*) zet het terug via `restore_config_file`.
- **`set_yaml_key` met validatie** — voeg, vervang of verwijder een enkele
  top-level YAML-key met automatische `check_config`-validatie ná de wijziging.
  Installeer `home-assistant-mcp[yaml]` voor comment-preserving YAML-edits via
  `ruamel.yaml`; zonder die extra gebruikt de tool een eenvoudige fallback.
- **Back-up & restore** — laat Claude vóór grote ingrepen een volledige back-up
  maken (`create_backup`) en desnoods de hele installatie terugzetten
  (`restore_backup`). Stel `HA_AUTO_BACKUP_BEFORE_UPDATE=true` in om automatisch
  te back-uppen vóór elke update.
- **Bevestiging vereist** voor risicovolle acties (`confirm=true`): herstarten,
  verwijderen, updates installeren, integraties/add-ons verwijderen, host
  rebooten, back-ups terugzetten.
- **`check_config` vóór herstart** — laat Claude de configuratie eerst valideren.
- **Veilige modus** — zet `HA_READ_ONLY=true` en Claude mag wél alles lezen en
  analyseren, maar niets wijzigen. Ideaal om eerst rond te kijken.
- **Per-tool uitschakelen** — met `HA_DISABLED_TOOLS=reboot_host,restore_backup`
  zet je specifieke tools uit zonder de rest te beïnvloeden. Of gebruik
  `HA_ENABLED_TOOLS=list_entities,get_state,call_service` voor een strikte
  whitelist.

---

## 🌐 Transport: stdio, HTTP of SSE

De server ondersteunt drie transportmodi:

| Modus | wanneer te gebruiken | start-commando |
|-------|----------------------|----------------|
| **stdio** (standaard) | Client draait lokaal (Claude Code, Claude Desktop, Cursor) | `ha-mcp` |
| **HTTP** (Streamable HTTP) | Remote clients (ChatGPT, Open WebUI) of meerdere clients tegelijk | `ha-mcp --transport http --host 0.0.0.0 --port 8765` |
| **SSE** (Server-Sent Events) | Clients die SSE verlangen i.p.v. Streamable HTTP | `ha-mcp --transport sse --host 0.0.0.0 --port 8765` |

De transportmodus kan ook via env-var worden ingesteld: `HA_TRANSPORT=http`,
`HA_HOST=127.0.0.1`, `HA_PORT=8765`. Zet voor HTTP/SSE buiten je eigen machine
ook `HA_HTTP_TOKEN` en configureer je client met `Authorization: Bearer <token>`.

### Combined mode met HA's ingebouwde MCP

Home Assistant heeft ook een eigen MCP-endpoint op `/api/mcp` voor Assist-scoped
context. Deze server blijft de volledige configuratie/debug-laag, maar kan die
Assist-context als resource doorgeven:

```bash
HA_BUILTIN_MCP_URL=https://jouw-ha-url/api/mcp
```

Daarna is `homeassistant://assist/context-snapshot` beschikbaar in dezelfde
MCP-sessie.

### HA OS add-on

Deze repo bevat ook een eerste HA OS/Supervised add-on in
[`homeassistant-addon/`](./homeassistant-addon). Die draait de MCP-server binnen
Home Assistant met HTTP transport. Zet in de add-on opties altijd een lang
`http_token` en gebruik in je client `Authorization: Bearer <token>`.

> Clients die alleen stdio ondersteunen (zoals Claude Desktop) kunnen
> `mcp-proxy` gebruiken als gateway naar een HTTP-server. Zie
> [mcp-proxy](https://github.com/sparfenyuk/mcp-proxy).

---

## 🔧 Handmatig instellen (als je het zelf wilt doen)

<details>
<summary>Klik om uit te klappen</summary>

### 1. Token aanmaken
In Home Assistant: klik op je **gebruiker** (linksonder) → tabblad **Beveiliging**
→ **Langlevend toegangstoken aanmaken** → kopiëren.

### 2. YAML-bestandstoegang (aanbevolen op HA OS)
Installeer de add-on **Advanced SSH & Web Terminal**, zet een `password` en
`sftp: true`. De config-map is dan bereikbaar op `/config`.

### 3. Installeren
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[ssh,yaml]"   # of: pip install -e .  (zonder SSH/YAML-extra)
```

### 4. Configureren
Kopieer `.env.example` → `.env` en vul je gegevens in (zie het bestand voor uitleg).

### 5. Koppelen aan Claude Code
```bash
claude mcp add home-assistant \
  --env HA_URL=http://homeassistant.local:8123 \
  --env HA_TOKEN=eyJ... \
  --env HA_FILES_BACKEND=ssh \
  --env HA_SSH_HOST=homeassistant.local \
  --env HA_SSH_USER=root \
  --env HA_SSH_PASSWORD=... \
  -- /pad/naar/.venv/bin/ha-mcp
```
Of kopieer [`mcp.example.json`](./mcp.example.json) naar `.mcp.json` in je project.

### 6. HTTP-mode (voor remote clients)
```bash
ha-mcp --transport http --host 0.0.0.0 --port 8765
```
Configureer je client met de URL `http://jouw-pc:8765/mcp`.

</details>

---

## ⚙️ Alle configuratie-opties

| Variabele | Standaard | Beschrijving |
|-----------|-----------|--------------|
| `HA_URL` | — | Webadres van je Home Assistant |
| `HA_TOKEN` | — | Long-Lived Access Token |
| `HA_VERIFY_SSL` | `true` | SSL-certificaten controleren (zet `false` bij self-signed) |
| `HA_TIMEOUT` | `30` | Timeout in seconden voor API-calls |
| `HA_FILES_BACKEND` | `none` | Bestandstoegang: `none`, `local` of `ssh` |
| `HA_CONFIG_DIR` | — | Pad naar HA config-map (voor `local` backend) |
| `HA_SSH_HOST` | — | SSH-host (voor `ssh` backend) |
| `HA_SSH_PORT` | `22` | SSH-poort |
| `HA_SSH_USER` | — | SSH-gebruiker |
| `HA_SSH_PASSWORD` | — | SSH-wachtwoord |
| `HA_SSH_KEY_FILE` | — | Pad naar SSH private key (i.p.v. wachtwoord) |
| `HA_SSH_CONFIG_DIR` | `/config` | Config-map op de SSH-host |
| `HA_READ_ONLY` | `false` | Veilige modus: alleen lezen, niets wijzigen |
| `HA_SNAPSHOTS` | `true` | Lokale snapshots vóór YAML-wijzigingen |
| `HA_SNAPSHOT_DIR` | `~/.ha-mcp/snapshots` | Waar snapshots worden opgeslagen |
| `HA_AUTO_BACKUP_BEFORE_UPDATE` | `false` | Automatisch back-up vóór updates |
| `HA_DISABLED_TOOLS` | — | Comma-gescheiden lijst van uit te schakelen tools |
| `HA_ENABLED_TOOLS` | — | Whitelist: alleen deze tools exposen |
| `HA_ENABLE_TOOL_SEARCH` | `false` | Search-based tool-discovery aanzetten |
| `HA_TOOL_SEARCH_MAX_RESULTS` | `5` | Max zoekresultaten (2–10) |
| `HA_PINNED_TOOLS` | — | Tools die altijd zichtbaar blijven in search-mode |
| `HA_TRANSPORT` | `stdio` | Transport: `stdio`, `sse` of `http` |
| `HA_HOST` | `127.0.0.1` | Bind-adres voor HTTP/SSE |
| `HA_PORT` | `8765` | Bind-poort voor HTTP/SSE |
| `HA_HTTP_TOKEN` | — | Optionele Bearer-tokenbeveiliging voor HTTP/SSE |
| `HA_BUILTIN_MCP_URL` | — | Optionele proxy naar HA's eigen `/api/mcp` combined mode |
| `HA_LOG_LEVEL` | `warning` | Log-niveau van de MCP-server zelf (stderr) |
| `HA_SNAPSHOT_KEEP` | `30` | Aantal snapshots dat per bestand bewaard blijft |
| `HA_SSH_KNOWN_HOSTS` | `~/.ha-mcp/known_hosts` | Waar SSH host keys onthouden worden (trust-on-first-use) |

Zie [`.env.example`](./.env.example) voor gedetailleerde uitleg per variabele.

---

## 🔒 Veiligheid & het vertrouwensmodel

Je geeft veel toegang, dus dit is belangrijk. Zo is het opgezet:

- **Geen cloud, geen tussenpartij.** De server draait op jóuw computer en praat
  rechtstreeks met jouw Home Assistant. Je token verlaat je netwerk niet.
- **Versleutelde verbinding.** Gebruik waar mogelijk een **https**-adres (bijv.
  via Nabu Casa of een reverse proxy). De wizard waarschuwt bij een
  onversleutelde verbinding naar een adres buiten je eigen netwerk.
- **Geheimen afgeschermd.** De wizard zet `.env` en `.mcp.json` op
  `chmod 600` (alleen voor jou leesbaar). Beide staan in `.gitignore`.
- **SSH met sleutel.** Bij bestandstoegang kun je een SSH-**sleutel** kiezen in
  plaats van een wachtwoord (`HA_SSH_KEY_FILE`).
- **SSH host key-controle.** Host keys worden bij de eerste verbinding
  onthouden (`~/.ha-mcp/known_hosts`); een gewijzigde key wordt daarna
  geweigerd (bescherming tegen MITM).
- **Minimale rechten (aanrader).** Maak in Home Assistant een **aparte gebruiker**
  voor Claude en maak het token onder die gebruiker aan. Zo kun je de toegang in
  één klik intrekken (Instellingen → Personen → gebruiker → token verwijderen).
- **Padbeveiliging.** De bestands-backends houden elk pad **binnen** je
  config-map (geen `../`-ontsnapping).
- **Read-only / veilige modus.** `HA_READ_ONLY=true` blokkeert alle acties
  die apparaten, dashboards, integraties of YAML-bestanden wijzigen. De
  onschuldige status-heartbeat naar Claude Link blijft toegestaan, zodat je in
  Home Assistant nog steeds ziet of de koppeling leeft.
- **Per-tool beveiliging.** Schakel specifieke tools uit met `HA_DISABLED_TOOLS`
  of beperk tot een whitelist met `HA_ENABLED_TOOLS`.
- **Bevestiging + rollback** voor alles wat impact heeft (zie *Fool-proof* hierboven).

> Een token intrekken? Verwijder het in Home Assistant bij je gebruiker → tabblad
> **Beveiliging**. De koppeling werkt dan direct niet meer.

---

## 🗂️ Structuur

```
src/ha_mcp/                        # de MCP-server (Python)
  __main__.py                      #   entry-point (--transport stdio/sse/http)
  app.py                           #   gedeelde objecten + activiteits-heartbeat + tool-filter
  config.py                        #   env-driven configuratie (Settings)
  ha_client.py                     #   REST + WebSocket client (+ read-only handhaving)
  files.py                         #   local & ssh bestands-backends (met padbeveiliging)
  snapshots.py                     #   lokale snapshots voor omkeerbare bestandswijzigingen (met pruning)
  yaml_edit.py                     #   pure YAML-editlogica voor set_yaml_key (getest)
  server.py                        #   import → registreert alle tools + resources + discovery
  resources.py                     #   MCP Resources (homeassistant://overview, /services, …)
  setup.py                         #   de interactieve wizard (ha-mcp-setup, 9 clients)
  doctor.py                        #   de gezondheidscheck (ha-mcp-doctor)
  dashboard_template.py            #   het automatische Claude Link dashboard
  tools/                           #   alle 141 tools + workflow-prompts, per thema
    core.py                        #     states, services, events, get_overview, fuzzy_search, bulk_control
    automations.py                 #     automations, scripts, scenes
    dashboards.py                  #     Lovelace dashboards
    helpers.py                     #     input_*, counter, timer, schedule
    registry.py                    #     areas, floors, devices, entities, labels, persons, zones, config entries, entity exposure
    supervisor.py                  #     add-ons, back-ups, logs, host, supervisor
    system.py                      #     config, check_config, restart, reload, notifications, updates
    maintenance.py                 #     log levels, purge, mqtt, energy, diagnose
    templates.py                   #     render_template, history, logbook, error_log, statistics
    files_tools.py                 #     list/read/write/delete config files, set_yaml_key, snapshots
    todo.py                        #     todo-lijsten (REST service calls)
    calendar.py                    #     kalenders (REST + WS)
    camera.py                      #     camera-snapshots (base64)
    blueprints.py                  #     automation/script blueprints
    groups.py                      #     entity-groepen (group.set/remove)
    traces.py                      #     automation-traces (debugging)
    voice.py                       #     Assist: converse + pipelines
    discovery.py                   #     tool-search proxy (search_tools, call_read/write/delete_tool)
    prompts.py                     #     5 workflow-prompts (slash-commando's)
custom_components/claude_link/     # de HACS-integratie (status + dashboard in HA)
install.sh / install.ps1           # één-commando installers
hacs.json                          # HACS-metadata
mcp.example.json                   # voorbeeld-configuratie (stdio + HTTP)
.env.example                       # alle configuratie-opties met uitleg
```

---

## 📋 Systeemvereisten

- **Home Assistant** 2026.6 of nieuwer
- **Python** 3.10 of nieuwer (op de machine waar de MCP-server draait)
- **HACS** geïnstalleerd in Home Assistant (voor de Claude Link integratie)
- Optioneel: **Advanced SSH & Web Terminal** add-on (voor YAML-bestandstoegang op HA OS)

---

## Licentie

Mark Salama
