"""Pure helpers for editing a single top-level key in a YAML document.

Used by the `set_yaml_key` tool. When ruamel.yaml is available we do a
comment-preserving round-trip edit; otherwise a conservative text-based
fallback handles simple top-level keys. Keeping this logic free of I/O makes
it unit-testable.
"""

from __future__ import annotations

import re


def have_ruamel() -> bool:
    try:
        import ruamel.yaml  # noqa: F401
        return True
    except ImportError:
        return False


def edit_with_ruamel(content: str, key: str, value: str | None) -> str:
    """Comment-preserving edit: set or remove one top-level key."""
    from io import StringIO

    from ruamel.yaml import YAML

    yaml_lib = YAML()
    parsed = yaml_lib.load(content)
    if parsed is None:
        parsed = {}
    if value is None:
        parsed.pop(key, None)
    else:
        val_parsed = yaml_lib.load(value)
        parsed[key] = val_parsed if val_parsed is not None else value
    buf = StringIO()
    yaml_lib.dump(parsed, buf)
    return buf.getvalue()


def _find_key_block(lines: list[str], key: str) -> tuple[int | None, int]:
    """Return (start, end) line indices of a top-level key block.

    `start` is None when the key is not present. `end` is the index of the
    first line after the block (the next top-level key, or end of file).
    """
    key_pattern = re.compile(rf"^{re.escape(key)}\s*:")
    start: int | None = None
    end = len(lines)
    for i, line in enumerate(lines):
        if start is None:
            if key_pattern.match(line):
                start = i
        else:
            stripped = line.rstrip("\r\n")
            if stripped and not stripped[0].isspace() and not stripped.startswith("#"):
                end = i
                break
    return start, end


def _render_block(key: str, value: str) -> str:
    value_lines = value.splitlines()
    if len(value_lines) <= 1 and not value.strip().startswith("-"):
        return f"{key}: {value.strip()}\n"
    block = f"{key}:\n"
    for vl in value_lines:
        block += f"  {vl}\n" if vl.strip() else "\n"
    return block


def edit_with_text_fallback(content: str, key: str, value: str | None) -> tuple[str, bool]:
    """Set or remove one top-level key using plain text manipulation.

    Returns (new_content, changed). Only handles top-level keys; nested keys
    need the ruamel path.
    """
    lines = content.splitlines(keepends=True)
    start, end = _find_key_block(lines, key)

    if value is None:
        if start is None:
            return content, False
        return "".join(lines[:start] + lines[end:]), True

    new_block = _render_block(key, value)
    if start is not None:
        return "".join(lines[:start] + [new_block] + lines[end:]), True

    # Append at the end, ensuring exactly one blank separator line.
    out = "".join(lines)
    if out and not out.endswith("\n"):
        out += "\n"
    if out.strip():
        out += "\n"
    return out + new_block, True
