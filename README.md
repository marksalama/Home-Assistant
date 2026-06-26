# Home Assistant ↔ Claude Code

Geef **Claude Code** zo veel mogelijk controle over je **Home Assistant** —
uitlezen, bedienen én aanpassen — met een visuele, gebruiksvriendelijke kant
ín Home Assistant zelf.

Dit project bestaat uit **drie onderdelen**:

| Onderdeel | Wat het doet | Waar het draait |
|-----------|--------------|-----------------|
| 🧠 **MCP-server** | 100 tools waarmee Claude je HA bestuurt, configureert, beheert en debugt (REST + WebSocket API + ruwe YAML-bestanden) | Op je computer, naast Claude Code |
| 🏠 **Claude Link** (integratie) | Visuele status-tegels + automatisch dashboard in Home Assistant, installeerbaar via **HACS** | In Home Assistant |
| ✨ **Setup-wizard** | Zet alles automatisch op: verbinding testen, koppelen aan Claude Code, dashboard aanmaken | Eén commando |

> Gemaakt voor **HA OS / Supervised** (jij hebt HACS) — werkt ook op Container/Core.

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
5. **koppelt** de server automatisch aan Claude Code en schrijft `.env` + `.mcp.json`;
6. **maakt** het *Claude Link*-dashboard automatisch in Home Assistant aan.

Daarna: **herstart Claude Code** en typ `/mcp` — je ziet `home-assistant` als verbonden.

### Stap 2 — De visuele integratie installeren (via HACS)

1. Open in Home Assistant **HACS**.
2. Klik rechtsboven op de drie puntjes → **Aangepaste repository's** (Custom repositories).
3. Plak de URL van deze repository en kies categorie **Integratie** (Integration). Klik **Toevoegen**.
4. Zoek **Claude Link** in HACS, klik **Downloaden**, en **herstart Home Assistant**.
5. Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen**, zoek **Claude Link** en klik op **Verzenden**.

Je krijgt nu in Home Assistant:

- een apparaat **Claude Link** met tegels: *Verbonden*, *Laatste activiteit*, *Aantal acties* en een knop *Maak back-up*;
- een **dashboard** in de zijbalk dat je de status laat zien.

Klaar! 🎉

---

## 💬 Wat kun je nu tegen Claude zeggen?

- "Zet alle lampen in de woonkamer op 30%."
- "Maak een scene 'filmavond' met gedimd licht en de tv aan."
- "Schrijf een automation die de buitenverlichting bij zonsondergang aanzet."
- "Laat de error log zien en los de waarschuwingen op."
- "Voeg een helper `vakantiemodus` toe en gebruik die in een automation."
- "Open `configuration.yaml`, voeg een template-sensor toe, valideer en herstart."
- "Maak een back-up en update de Mosquitto add-on."
- "Maak een nieuw dashboard met een kaart per kamer."

---

## 🧰 Wat de MCP-server allemaal kan (100 tools)

| Categorie | Tools |
|-----------|-------|
| **States & besturing** | `list_entities`, `get_state`, `set_state`, `call_service`, `fire_event`, `list_services` |
| **Automations** | `list/get/upsert/delete/trigger_automation` |
| **Scripts** | `list/get/upsert/delete/run_script` |
| **Scenes** | `list/get/upsert/delete/activate_scene` |
| **Dashboards** | `list/get/save/create_dashboard` |
| **Helpers** | `list/create/update/delete_helper` (input_*, counter, timer, schedule) |
| **Areas & floors** | `list/create/update/delete_area`, `list/create/update/delete_floor` |
| **Devices & entities** | `list/update_device`, `list_entity_registry`, `update_entity` |
| **Labels, personen, zones** | `list/create/delete_label`, `list_persons`, `list/create_zone` |
| **Integraties** | `list/reload/delete_config_entry` |
| **Add-on-beheer** (HA OS) | `list_addons`, `list_available_addons`, `get_addon_info/stats/changelog/logs`, `install_addon`, `uninstall_addon`, `set_addon_options`, `control_addon` (start/stop/restart/update/rebuild) |
| **Back-ups & rollback** | `list/create/restore/delete_backup`, `list_file_snapshots`, `restore_config_file` |
| **Debug & onderhoud** | `get_core/supervisor/host_logs`, `get_error_log`, `set_log_level`, `set_default_log_level`, `diagnose_entity`, `purge_database`, `system_health` |
| **Systeem** | `get_config`, `check_config`, `restart_home_assistant`, `reload_domain`, `update_supervisor`, `reboot_host` |
| **MQTT & energie** | `mqtt_publish`, `get_energy_prefs`, `save_energy_prefs` |
| **Meldingen & updates** | `list/create/dismiss_notification`, `notify`, `list_updates`, `install_update` (met back-up) |
| **Templates & data** | `render_template`, `get_history`, `get_logbook`, `get_statistics` |
| **YAML-bestanden** | `list/read/write/delete_config_file` (met automatische snapshots) |

---

## 🛟 Fool-proof: niets gaat onomkeerbaar stuk

Veiligheid zit standaard ingebouwd, zodat je rustig kunt experimenteren:

- **Automatische snapshots** — elke keer dat Claude een YAML-bestand wijzigt of
  verwijdert, wordt de vorige versie lokaal bewaard. Eén opdracht (*"draai die
  wijziging terug"*) zet het terug via `restore_config_file`.
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
pip install -e ".[ssh]"   # of: pip install -e .  (zonder SSH)
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

</details>

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
- **Minimale rechten (aanrader).** Maak in Home Assistant een **aparte gebruiker**
  voor Claude en maak het token onder die gebruiker aan. Zo kun je de toegang in
  één klik intrekken (Instellingen → Personen → gebruiker → token verwijderen).
- **Padbeveiliging.** De bestands-backends houden elk pad **binnen** je
  config-map (geen `../`-ontsnapping).
- **Read-only / veilige modus.** `HA_READ_ONLY=true` blokkeert centraal álle
  wijzigende acties (REST én WebSocket).
- **Bevestiging + rollback** voor alles wat impact heeft (zie *Fool-proof* hierboven).

> Een token intrekken? Verwijder het in Home Assistant bij je gebruiker → tabblad
> **Beveiliging**. De koppeling werkt dan direct niet meer.

## 🗂️ Structuur

```
src/ha_mcp/            # de MCP-server (Python)
  app.py               #   gedeelde objecten + activiteits-heartbeat
  ha_client.py         #   REST + WebSocket client (+ read-only handhaving)
  files.py             #   local & ssh bestands-backends (met padbeveiliging)
  snapshots.py         #   lokale snapshots voor omkeerbare bestandswijzigingen
  setup.py             #   de interactieve wizard (ha-mcp-setup)
  dashboard_template.py#   het automatische dashboard
  tools/               #   alle 100 tools, per thema
custom_components/claude_link/   # de HACS-integratie (status + dashboard in HA)
install.sh / install.ps1         # één-commando installers
hacs.json                        # HACS-metadata
```

## Licentie

MIT
