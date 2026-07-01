"""Local snapshot store for safe, reversible config file edits.

Before any config file is overwritten or deleted, its previous contents are
saved here with a timestamp. This gives instant per-file rollback ("undo")
without needing a slow full Home Assistant backup, and works the same for both
the local and ssh file backends (snapshots always live on the machine running
this server).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class SnapshotInfo:
    version: str  # timestamp id
    path: str
    size: int
    created: str


def _slug(path: str) -> str:
    """Filesystem-safe directory name for a config-relative path."""
    digest = hashlib.sha1(path.encode("utf-8")).hexdigest()[:10]
    flat = path.replace("/", "__").replace("\\", "__") or "root"
    return f"{flat[:60]}-{digest}"


class SnapshotStore:
    def __init__(self, base_dir: str, keep: int = 30) -> None:
        self.base = Path(base_dir).expanduser()
        self.keep = max(1, keep)

    def _dir_for(self, path: str) -> Path:
        return self.base / _slug(path)

    def save(self, path: str, content: str) -> SnapshotInfo:
        """Store a snapshot of `content` for config-relative `path`."""
        d = self._dir_for(path)
        d.mkdir(parents=True, exist_ok=True)
        version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        (d / f"{version}.snapshot").write_text(content, encoding="utf-8")
        meta = {"path": path, "version": version,
                "created": datetime.now(timezone.utc).isoformat()}
        (d / f"{version}.json").write_text(json.dumps(meta), encoding="utf-8")
        self._prune(d)
        return SnapshotInfo(version=version, path=path,
                            size=len(content.encode("utf-8")), created=meta["created"])

    def _prune(self, d: Path) -> None:
        """Keep only the newest `keep` snapshots per file (bounded disk usage)."""
        snaps = sorted(d.glob("*.snapshot"), reverse=True)
        for old in snaps[self.keep:]:
            meta = d / f"{old.stem}.json"
            try:
                old.unlink()
                if meta.is_file():
                    meta.unlink()
            except OSError:
                pass

    def list(self, path: str) -> list[SnapshotInfo]:
        d = self._dir_for(path)
        if not d.is_dir():
            return []
        out: list[SnapshotInfo] = []
        for snap in sorted(d.glob("*.snapshot"), reverse=True):
            version = snap.stem
            meta_file = d / f"{version}.json"
            created = ""
            if meta_file.is_file():
                try:
                    created = json.loads(meta_file.read_text(encoding="utf-8")).get("created", "")
                except (json.JSONDecodeError, OSError):
                    pass
            out.append(SnapshotInfo(version=version, path=path,
                                    size=snap.stat().st_size, created=created))
        return out

    def read(self, path: str, version: str | None = None) -> str:
        """Return snapshot content; latest if version is None."""
        d = self._dir_for(path)
        if version:
            snap = d / f"{version}.snapshot"
        else:
            snaps = sorted(d.glob("*.snapshot"), reverse=True)
            if not snaps:
                raise FileNotFoundError(f"No snapshots for {path!r}")
            snap = snaps[0]
        if not snap.is_file():
            raise FileNotFoundError(f"Snapshot not found: {path!r} @ {version}")
        return snap.read_text(encoding="utf-8")
