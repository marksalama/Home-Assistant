"""Unit tests for the YAML single-key edit helpers."""

from __future__ import annotations

from ha_mcp.yaml_edit import edit_with_text_fallback

DOC = """\
# my config
homeassistant:
  name: Home

sensor:
  - platform: template
    sensors: {}

script: !include scripts.yaml
"""


class TestTextFallback:
    def test_replace_existing_key(self) -> None:
        out, changed = edit_with_text_fallback(DOC, "script", "!include other.yaml")
        assert changed
        assert "script: !include other.yaml\n" in out
        assert "scripts.yaml" not in out
        # untouched parts stay intact, including comments
        assert "# my config" in out
        assert "homeassistant:" in out

    def test_replace_block_key(self) -> None:
        out, changed = edit_with_text_fallback(DOC, "sensor", "- platform: demo")
        assert changed
        assert "sensor:\n  - platform: demo\n" in out
        assert "template" not in out

    def test_append_new_key(self) -> None:
        out, changed = edit_with_text_fallback(DOC, "input_boolean", "vacation:\n  name: Vakantie")
        assert changed
        assert out.endswith("input_boolean:\n  vacation:\n    name: Vakantie\n")

    def test_append_scalar_key(self) -> None:
        out, changed = edit_with_text_fallback("a: 1\n", "b", "2")
        assert changed
        assert out == "a: 1\n\nb: 2\n"

    def test_remove_key(self) -> None:
        out, changed = edit_with_text_fallback(DOC, "sensor", None)
        assert changed
        assert "sensor:" not in out
        assert "script: !include scripts.yaml" in out

    def test_remove_missing_key_is_noop(self) -> None:
        out, changed = edit_with_text_fallback(DOC, "does_not_exist", None)
        assert not changed
        assert out == DOC

    def test_similar_prefix_not_matched(self) -> None:
        doc = "sensor_extra: 1\nsensor: 2\n"
        out, changed = edit_with_text_fallback(doc, "sensor", "3")
        assert changed
        assert "sensor_extra: 1" in out
        assert "sensor: 3" in out
