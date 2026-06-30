"""Opt-in probes for the live Home Assistant API contracts.

Run with:
    HA_MCP_RUN_INTEGRATION_TESTS=1 pytest tests/integration
"""

from __future__ import annotations

import asyncio
import os

import pytest

from ha_mcp.config import load_settings
from ha_mcp.ha_client import HAClient

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("HA_MCP_RUN_INTEGRATION_TESTS") != "1",
    reason=(
        "Live Home Assistant integration tests are opt-in. "
        "Set HA_MCP_RUN_INTEGRATION_TESTS=1 to run them."
    ),
)
def test_safe_rest_and_ws_contracts() -> None:
    async def _run() -> None:
        settings = load_settings()
        client = HAClient(settings)
        try:
            config = await client.rest_get("/config")
            assert isinstance(config, dict)
            assert config.get("version")

            states = await client.rest_get("/states")
            assert isinstance(states, list)

            services = await client.rest_get("/services")
            assert isinstance(services, list)

            ws_checks = [
                ("areas", {"type": "config/area_registry/list"}),
                ("devices", {"type": "config/device_registry/list"}),
                ("entities", {"type": "config/entity_registry/list"}),
                ("labels", {"type": "config/label_registry/list"}),
                ("integrations", {"type": "config_entries/get"}),
                ("system_log", {"type": "system_log/list"}),
            ]
            for name, command in ws_checks:
                result = await client.ws_command(command)
                assert isinstance(result, list), name
        finally:
            await client.aclose()

    asyncio.run(_run())
