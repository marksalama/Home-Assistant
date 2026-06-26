# Home Assistant ↔ Claude Code

Geef **Claude Code** zo veel mogelijk controle over je **Home Assistant** —
uitlezen, bedienen én aanpassen — met een visuele, gebruiksvriendelijke kant
ín Home Assistant zelf.

Dit project bestaat uit **drie onderdelen**:

| Onderdeel | Wat het doet | Waar het draait |
|-----------|--------------|-----------------|
| 🧠 **MCP-server** | 78 tools waarmee Claude je HA bestuurt en configureert (REST + WebSocket API + ruwe YAML-bestanden) | Op je computer, naast Claude Code |
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

## 🧰 Wat de MCP-server allemaal kan (78 tools)

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
| **Add-ons & back-ups** (HA OS) | `list_addons`, `get_addon_info`, `control_addon`, `get_addon_logs`, `list/create_backup`, `supervisor_info`, `host_info` |
| **Systeem** | `get_config`, `check_config`, `restart_home_assistant`, `reload_domain`, `system_health` |
| **Meldingen & updates** | `list/create/dismiss_notification`, `notify`, `list_updates`, `install_update` |
| **Templates & data** | `render_template`, `get_history`, `get_logbook`, `get_error_log`, `get_statistics` |
| **YAML-bestanden** | `list/read/write/delete_config_file` |

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

## 🔒 Veiligheid

- Het token en SSH-wachtwoord geven **volledige controle** over je Home
  Assistant. `.env` en `.mcp.json` staan in `.gitignore`.
- De bestands-backends houden elk pad **binnen** je config-map (geen `../`).
- Risicovolle acties vereisen een expliciete bevestiging: `restart_home_assistant`,
  `delete_config_file`, `delete_config_entry`, `install_update` (allemaal `confirm=True`).
- Bewerk je YAML? Laat Claude eerst `check_config()` draaien vóór een herstart.

## 🗂️ Structuur

```
src/ha_mcp/            # de MCP-server (Python)
  app.py               #   gedeelde objecten + activiteits-heartbeat
  ha_client.py         #   REST + WebSocket client
  files.py             #   local & ssh bestands-backends (met padbeveiliging)
  setup.py             #   de interactieve wizard (ha-mcp-setup)
  dashboard_template.py#   het automatische dashboard
  tools/               #   alle 78 tools, per thema
custom_components/claude_link/   # de HACS-integratie (status + dashboard in HA)
install.sh / install.ps1         # één-commando installers
hacs.json                        # HACS-metadata
```

## Licentie

MIT
