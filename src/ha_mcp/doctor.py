"""Health check: `ha-mcp-doctor` verifies the whole setup in plain language.

Run it any time something seems off. It checks the connection, the WebSocket
API, optional file access, the Claude Link integration and the permissions on
your secrets file, and prints clear ✅/⚠️/❌ results with hints.
"""

from __future__ import annotations

import asyncio
import os
import stat
import sys
from pathlib import Path

from .config import load_settings
from .files import get_backend
from .ha_client import HAClient


def _line(symbol: str, msg: str) -> None:
    print(f"{symbol} {msg}")


def _configure_output() -> None:
    """Avoid UnicodeEncodeError on Windows consoles/pipes with legacy encodings."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


async def _run() -> int:
    problems = 0
    try:
        settings = load_settings()
    except SystemExit as exc:
        _line("❌", f"Configuratie ontbreekt: {exc}")
        _line("➡️", "Draai eerst de wizard: ha-mcp-setup")
        return 1

    _line("ℹ️", f"Home Assistant: {settings.ha_url}")
    if settings.read_only:
        _line("ℹ️", "Veilige modus (HA_READ_ONLY) staat AAN — wijzigingen zijn geblokkeerd.")

    client = HAClient(settings)
    try:
        # 1. REST connection
        try:
            cfg = await client.rest_get("/config")
            _line("✅", f"Verbonden (Home Assistant {cfg.get('version')}, {cfg.get('location_name')}).")
        except Exception as exc:  # noqa: BLE001
            _line("❌", f"Geen verbinding/REST: {exc}")
            _line("➡️", "Controleer HA_URL en HA_TOKEN. Token verlopen? Maak een nieuwe aan.")
            return 1

        # 2. WebSocket
        try:
            areas = await client.ws_command({"type": "config/area_registry/list"})
            _line("✅", f"WebSocket API werkt ({len(areas)} areas gevonden).")
        except Exception as exc:  # noqa: BLE001
            problems += 1
            _line("⚠️", f"WebSocket API werkt niet: {exc}")

        # 3. File backend
        if settings.files_backend in ("local", "ssh"):
            try:
                backend = get_backend(settings)
                entries = await asyncio.to_thread(backend.list_dir, "")
                names = [e.name for e in entries]
                ok = "configuration.yaml" in names
                _line("✅" if ok else "⚠️",
                      f"Bestandstoegang ({settings.files_backend}) werkt"
                      + ("." if ok else " maar configuration.yaml niet gezien."))
            except Exception as exc:  # noqa: BLE001
                problems += 1
                _line("⚠️", f"Bestandstoegang werkt niet: {exc}")
                if "Unable to connect to port" in str(exc):
                    _line(
                        "➡️",
                        "De SSH-host klopt, maar poort 22 is niet bereikbaar. "
                        "Start de SSH-add-on en zet de netwerkpoort op 22.",
                    )
                elif "getaddrinfo" in str(exc):
                    _line("➡️", "Het SSH-adres is geen geldige hostnaam. Gebruik alleen bijvoorbeeld homeassistant.local.")
                else:
                    _line("➡️", "Controleer de SSH-add-on en je SSH-gegevens.")
        else:
            _line("ℹ️", "Bestandstoegang staat uit (HA_FILES_BACKEND=none). YAML bewerken kan niet.")

        # 4. Claude Link integration
        try:
            services = await client.rest_get("/services")
            has_link = any(s.get("domain") == "claude_link" for s in services)
            if has_link:
                _line("✅", "Claude Link-integratie gevonden in Home Assistant.")
            else:
                _line("ℹ️", "Claude Link-integratie niet gevonden (optioneel) — installeer via HACS voor status-tegels.")
        except Exception:  # noqa: BLE001
            pass

        # 5. Supervisor API access for add-on/host/low-level backup tools.
        try:
            await client.rest_get("/hassio/supervisor/info")
            _line("✅", "Supervisor API werkt; add-on en host-tools zijn beschikbaar.")
        except Exception as exc:  # noqa: BLE001
            if "HTTP 401" in str(exc):
                try:
                    await client.ws_command(
                        {
                            "type": "supervisor/api",
                            "endpoint": "/supervisor/info",
                            "method": "get",
                        }
                    )
                    _line("✅", "Supervisor API werkt via WebSocket fallback.")
                except Exception as ws_exc:  # noqa: BLE001
                    _line(
                        "ℹ️",
                        "Supervisor API geeft 401 via REST en werkt ook niet via "
                        f"WebSocket fallback: {ws_exc}",
                    )
            elif "HTTP 404" in str(exc):
                _line("ℹ️", "Supervisor API niet gevonden; dit is normaal bij HA Container/Core.")
    finally:
        await client.aclose()

    # 6. Secret file permissions
    if os.name == "nt":
        _line("ℹ️", "Windows gebruikt ACL-rechten; POSIX chmod-controle overgeslagen.")
    for name in () if os.name == "nt" else (".env", ".mcp.json"):
        p = Path.cwd() / name
        if p.exists():
            mode = stat.S_IMODE(p.stat().st_mode)
            if mode & 0o077:
                problems += 1
                _line("⚠️", f"{name} is ook door anderen leesbaar. Beveilig met: chmod 600 {name}")
            else:
                _line("✅", f"{name} is goed afgeschermd.")

    print()
    if problems == 0:
        _line("🎉", "Alles ziet er goed uit!")
    else:
        _line("⚠️", f"{problems} aandachtspunt(en) gevonden — zie de tips hierboven.")
    return 0


def main() -> None:
    _configure_output()
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
