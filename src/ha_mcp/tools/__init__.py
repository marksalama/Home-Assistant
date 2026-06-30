"""Importing this package registers every tool on the shared FastMCP instance."""

from . import (  # noqa: F401
    automations,
    blueprints,
    calendar,
    camera,
    core,
    dashboards,
    files_tools,
    groups,
    hacs,
    helpers,
    installer,
    issues,
    maintenance,
    prompts,
    registry,
    skills,
    supervisor,
    system,
    templates,
    themes,
    todo,
    traces,
    discovery,  # imported last so _classify_tools sees all registered tools
)
