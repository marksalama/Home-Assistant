# Home Assistant MCP server

Een [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server
waarmee **Claude Code** zo veel mogelijk van jouw Home Assistant-installatie kan
**uitlezen, besturen én aanpassen** — inclusief het bewerken van ruwe
YAML-configuratiebestanden.

De server praat met Home Assistant via:

- de **REST API** en **WebSocket API** (met een Long-Lived Access Token), voor
  entiteiten, services, areas, devices, registries, helpers, automations,
  templates, history en systeembeheer;
- een optionele **bestands-backend** (lokaal pad of SSH/SFTP) om
  `configuration.yaml` en andere bestanden direct te lezen en te schrijven.

> Getest tegen Home Assistant op een **HA OS / Supervised** installatie.

---

## Wat kan Claude hiermee doen?

| Categorie | Tools |
|-----------|-------|
| **States & besturing** | `list_entities`, `get_state`, `set_state`, `call_service`, `fire_event` |
| **Ontdekken** | `list_services`, `list_areas`, `list_devices`, `list_entity_registry`, `list_labels`, `list_config_entries` |
| **Areas beheren** | `create_area`, `update_area`, `delete_area`, `update_entity` |
| **Helpers** | `list_helpers`, `create_helper`, `update_helper`, `delete_helper` (input_boolean/number/text/select/datetime/button, counter, timer, schedule) |
| **Automations** | `get_automation`, `upsert_automation`, `delete_automation`, `trigger_automation` |
| **Templates & data** | `render_template`, `get_history`, `get_logbook`, `get_error_log` |
| **Systeem** | `get_config`, `check_config`, `reload_domain`, `restart_home_assistant` |
| **YAML-bestanden** | `list_config_files`, `read_config_file`, `write_config_file`, `delete_config_file` |

Voorbeelden van wat je tegen Claude kunt zeggen:

- "Zet alle lampen in de woonkamer op 30%."
- "Maak een automation die om zonsondergang de buitenverlichting aanzet."
- "Laat de error log zien en los waarschuwingen op."
- "Voeg een input_boolean `vakantiemodus` toe en gebruik die in een automation."
- "Open `configuration.yaml`, voeg een `template`-sensor toe, valideer en herstart."

---

## 1. Vereisten

- Python **3.10+** op de machine waar Claude Code draait.
- Een bereikbare Home Assistant-instantie (bv. `http://homeassistant.local:8123`).

## 2. Long-Lived Access Token aanmaken

1. Open Home Assistant en klik linksonder op je **gebruikersnaam**.
2. Ga naar het tabblad **Beveiliging** (Security).
3. Onderaan bij **Langlevende toegangstokens** → **Token aanmaken**.
4. Geef het een naam (bv. `claude-code`) en **kopieer het token** (je ziet het
   maar één keer).

## 3. (Optioneel) Bestandstoegang voor YAML — aanbevolen op HA OS

Om `configuration.yaml` en andere bestanden te kunnen bewerken heb je toegang
tot de config-map nodig. Op **HA OS / Supervised** is de eenvoudigste route de
SSH-add-on:

1. **Instellingen → Add-ons → Add-on store**.
2. Installeer **Advanced SSH & Web Terminal** (van de Community add-ons).
3. Open de **Configuration** van de add-on en zet een `password` (of een
   `authorized_keys`), zet `username` op bv. `root` en stel `sftp: true` in.
4. Zet eventueel `Protection mode` **uit** als je volledige `/config`-toegang
   wilt, en start de add-on.

De config-map is via deze add-on bereikbaar op `/config`.

> Alternatief (Container/Core): gebruik de **local** backend en wijs
> `HA_CONFIG_DIR` naar je config-map (bv. een gemounte Samba-share).

## 4. Installeren

```bash
git clone <deze-repo> home-assistant-mcp
cd home-assistant-mcp

python3 -m venv .venv
source .venv/bin/activate

# Zonder SSH-bestandstoegang:
pip install -e .
# Mét SSH-bestandstoegang:
pip install -e ".[ssh]"
```

## 5. Configureren

Kopieer `.env.example` naar `.env` en vul je gegevens in:

```bash
cp .env.example .env
```

Belangrijkste variabelen:

```ini
HA_URL=http://homeassistant.local:8123
HA_TOKEN=eyJ...        # je Long-Lived token
HA_VERIFY_SSL=true

# YAML-bestandstoegang (kies none/local/ssh)
HA_FILES_BACKEND=ssh
HA_SSH_HOST=homeassistant.local
HA_SSH_USER=root
HA_SSH_PASSWORD=...    # wachtwoord van de SSH-add-on
HA_SSH_CONFIG_DIR=/config
```

## 6. Koppelen aan Claude Code

**Optie A — via de CLI** (vervang de waardes):

```bash
claude mcp add home-assistant \
  --env HA_URL=http://homeassistant.local:8123 \
  --env HA_TOKEN=eyJ... \
  --env HA_FILES_BACKEND=ssh \
  --env HA_SSH_HOST=homeassistant.local \
  --env HA_SSH_USER=root \
  --env HA_SSH_PASSWORD=... \
  --env HA_SSH_CONFIG_DIR=/config \
  -- /pad/naar/home-assistant-mcp/.venv/bin/ha-mcp
```

**Optie B — via een `.mcp.json`** in je project. Zie het meegeleverde
[`mcp.example.json`](./mcp.example.json) en kopieer het naar `.mcp.json` met je
eigen waardes. Gebruik het absolute pad naar `ha-mcp` in de venv als `command`,
of laat het `ha-mcp` zijn als de venv geactiveerd is.

Herstart daarna Claude Code en controleer met `/mcp` dat de server
`home-assistant` verbonden is.

## 7. Snel testen (zonder Claude)

```bash
# Toont een lijst met JSON-RPC tools als de server start (Ctrl-C om te stoppen)
.venv/bin/ha-mcp
```

Een handmatige rooktest van de verbinding:

```bash
.venv/bin/python -c "
import asyncio
from ha_mcp.config import load_settings
from ha_mcp.ha_client import HAClient
async def main():
    c = HAClient(load_settings())
    print((await c.rest_get('/config'))['version'])
    await c.aclose()
asyncio.run(main())
"
```

---

## Veiligheid

- Het token en SSH-wachtwoord geven **volledige controle** over je Home
  Assistant. Bewaar `.env`/`.mcp.json` veilig; ze staan in `.gitignore`.
- De bestands-backends houden elk pad **binnen** de geconfigureerde config-map
  (geen `../`-ontsnapping).
- Destructieve acties vragen een expliciete bevestiging:
  `restart_home_assistant(confirm=True)` en `delete_config_file(confirm=True)`.
- Bewerk je YAML? Roep eerst `check_config()` aan vóór een herstart.

## Architectuur

```
src/ha_mcp/
  config.py     # env/.env inladen -> Settings
  ha_client.py  # REST + WebSocket client (httpx, websockets)
  files.py      # local & ssh bestands-backends, met padbeveiliging
  server.py     # FastMCP server + alle tools
  __main__.py   # entrypoint (stdio transport)
```

## Licentie

MIT
