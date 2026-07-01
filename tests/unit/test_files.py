"""Unit tests for the file backend path sandbox."""

from __future__ import annotations

import pytest

from ha_mcp.files import LocalBackend, _normalize


class TestNormalize:
    def test_plain_relative_path(self) -> None:
        assert _normalize("configuration.yaml") == "configuration.yaml"

    def test_nested_path(self) -> None:
        assert _normalize("packages/lights.yaml") == "packages/lights.yaml"

    def test_leading_slash_is_stripped(self) -> None:
        assert _normalize("/configuration.yaml") == "configuration.yaml"

    def test_empty_means_root(self) -> None:
        assert _normalize("") == ""
        assert _normalize(".") == ""

    def test_dotdot_escape_rejected(self) -> None:
        with pytest.raises(ValueError):
            _normalize("../secrets.yaml")

    def test_hidden_dotdot_escape_rejected(self) -> None:
        with pytest.raises(ValueError):
            _normalize("packages/../../etc/passwd")

    def test_dotdot_inside_stays_when_resolvable(self) -> None:
        assert _normalize("packages/../configuration.yaml") == "configuration.yaml"


class TestLocalBackend:
    def test_read_write_roundtrip(self, tmp_path) -> None:
        backend = LocalBackend(str(tmp_path))
        backend.write("test.yaml", "a: 1\n")
        assert backend.read("test.yaml") == "a: 1\n"

    def test_write_outside_root_rejected(self, tmp_path) -> None:
        backend = LocalBackend(str(tmp_path))
        with pytest.raises(ValueError):
            backend.write("../evil.yaml", "x")

    def test_read_outside_root_rejected(self, tmp_path) -> None:
        backend = LocalBackend(str(tmp_path))
        with pytest.raises(ValueError):
            backend.read("subdir/../../evil.yaml")

    def test_symlink_escape_rejected(self, tmp_path) -> None:
        outside = tmp_path.parent / "outside-secret.txt"
        outside.write_text("secret")
        root = tmp_path / "config"
        root.mkdir()
        (root / "link").symlink_to(outside)
        backend = LocalBackend(str(root))
        with pytest.raises(ValueError):
            backend.read("link")

    def test_list_dir(self, tmp_path) -> None:
        backend = LocalBackend(str(tmp_path))
        backend.write("b.yaml", "x")
        (tmp_path / "subdir").mkdir()
        entries = backend.list_dir("")
        names = [e.name for e in entries]
        assert names == ["subdir", "b.yaml"]  # dirs first
