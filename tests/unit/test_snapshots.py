"""Unit tests for the snapshot store."""

from __future__ import annotations

import pytest

from ha_mcp.snapshots import SnapshotStore


def test_save_and_read_latest(tmp_path) -> None:
    store = SnapshotStore(str(tmp_path))
    store.save("configuration.yaml", "v1")
    store.save("configuration.yaml", "v2")
    assert store.read("configuration.yaml") == "v2"


def test_read_specific_version(tmp_path) -> None:
    store = SnapshotStore(str(tmp_path))
    info = store.save("configuration.yaml", "v1")
    store.save("configuration.yaml", "v2")
    assert store.read("configuration.yaml", info.version) == "v1"


def test_list_newest_first(tmp_path) -> None:
    store = SnapshotStore(str(tmp_path))
    first = store.save("a.yaml", "1")
    second = store.save("a.yaml", "2")
    versions = [s.version for s in store.list("a.yaml")]
    assert versions == sorted([first.version, second.version], reverse=True)


def test_list_unknown_path_is_empty(tmp_path) -> None:
    store = SnapshotStore(str(tmp_path))
    assert store.list("nope.yaml") == []


def test_read_without_snapshots_raises(tmp_path) -> None:
    store = SnapshotStore(str(tmp_path))
    with pytest.raises(FileNotFoundError):
        store.read("nope.yaml")


def test_prune_keeps_newest(tmp_path) -> None:
    store = SnapshotStore(str(tmp_path), keep=3)
    for i in range(6):
        store.save("configuration.yaml", f"v{i}")
    snaps = store.list("configuration.yaml")
    assert len(snaps) == 3
    assert store.read("configuration.yaml") == "v5"


def test_paths_do_not_collide(tmp_path) -> None:
    store = SnapshotStore(str(tmp_path))
    store.save("a/b.yaml", "ab")
    store.save("a__b.yaml", "a__b")
    assert store.read("a/b.yaml") == "ab"
    assert store.read("a__b.yaml") == "a__b"
