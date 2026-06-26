"""File backends for reading/writing raw Home Assistant config files (YAML etc.).

Two backends are supported:

* ``local`` - the HA config directory is reachable on the local filesystem
  (e.g. a mounted Samba share, or HA Core running in a venv).
* ``ssh``   - connect over SSH/SFTP (recommended for HA OS / Supervised using
  the "Advanced SSH & Web Terminal" add-on).

Both backends sandbox every path to the configured config directory so the
model can never read or write outside of it.
"""

from __future__ import annotations

import posixpath
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import Settings


class FilesDisabledError(RuntimeError):
    """Raised when a file tool is used but no file backend is configured."""


@dataclass
class FileEntry:
    name: str
    path: str
    is_dir: bool
    size: int


class FileBackend(Protocol):
    def list_dir(self, rel_path: str) -> list[FileEntry]: ...
    def read(self, rel_path: str) -> str: ...
    def write(self, rel_path: str, content: str) -> None: ...
    def delete(self, rel_path: str) -> None: ...


def _normalize(rel_path: str) -> str:
    """Normalize a user-supplied relative path and reject directory escapes."""
    rel = (rel_path or "").strip().lstrip("/")
    normalized = posixpath.normpath(rel) if rel else "."
    if normalized.startswith("..") or normalized == "..":
        raise ValueError(f"Path escapes the config directory: {rel_path!r}")
    return "" if normalized == "." else normalized


class LocalBackend:
    def __init__(self, config_dir: str) -> None:
        self.root = Path(config_dir).expanduser().resolve()
        if not self.root.is_dir():
            raise FilesDisabledError(f"HA_CONFIG_DIR does not exist: {self.root}")

    def _resolve(self, rel_path: str) -> Path:
        normalized = _normalize(rel_path)
        target = (self.root / normalized).resolve()
        if target != self.root and self.root not in target.parents:
            raise ValueError(f"Path escapes the config directory: {rel_path!r}")
        return target

    def list_dir(self, rel_path: str) -> list[FileEntry]:
        base = self._resolve(rel_path)
        entries: list[FileEntry] = []
        for child in sorted(base.iterdir(), key=lambda p: (p.is_file(), p.name)):
            rel = str(child.relative_to(self.root))
            entries.append(
                FileEntry(
                    name=child.name,
                    path=rel,
                    is_dir=child.is_dir(),
                    size=child.stat().st_size if child.is_file() else 0,
                )
            )
        return entries

    def read(self, rel_path: str) -> str:
        return self._resolve(rel_path).read_text(encoding="utf-8")

    def write(self, rel_path: str, content: str) -> None:
        target = self._resolve(rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def delete(self, rel_path: str) -> None:
        self._resolve(rel_path).unlink()


class SSHBackend:
    def __init__(self, settings: Settings) -> None:
        try:
            import paramiko  # noqa: F401
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise FilesDisabledError(
                "The ssh file backend needs paramiko. Install with: pip install 'home-assistant-mcp[ssh]'"
            ) from exc
        if not settings.ssh_host:
            raise FilesDisabledError("HA_SSH_HOST is required for the ssh backend.")
        self.s = settings
        self.root = posixpath.normpath(settings.ssh_config_dir)

    def _connect(self):
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs: dict = {
            "hostname": self.s.ssh_host,
            "port": self.s.ssh_port,
            "username": self.s.ssh_user,
            "timeout": self.s.timeout,
        }
        if self.s.ssh_key_file:
            connect_kwargs["key_filename"] = self.s.ssh_key_file
        if self.s.ssh_password:
            connect_kwargs["password"] = self.s.ssh_password
        client.connect(**connect_kwargs)
        return client

    def _resolve(self, rel_path: str) -> str:
        normalized = _normalize(rel_path)
        target = posixpath.normpath(posixpath.join(self.root, normalized))
        if target != self.root and not target.startswith(self.root + "/"):
            raise ValueError(f"Path escapes the config directory: {rel_path!r}")
        return target

    def list_dir(self, rel_path: str) -> list[FileEntry]:
        base = self._resolve(rel_path)
        client = self._connect()
        try:
            sftp = client.open_sftp()
            entries: list[FileEntry] = []
            for attr in sftp.listdir_attr(base):
                is_dir = stat.S_ISDIR(attr.st_mode or 0)
                full = posixpath.join(base, attr.filename)
                rel = posixpath.relpath(full, self.root)
                entries.append(
                    FileEntry(
                        name=attr.filename,
                        path=rel,
                        is_dir=is_dir,
                        size=0 if is_dir else (attr.st_size or 0),
                    )
                )
            entries.sort(key=lambda e: (not e.is_dir, e.name))
            return entries
        finally:
            client.close()

    def read(self, rel_path: str) -> str:
        target = self._resolve(rel_path)
        client = self._connect()
        try:
            sftp = client.open_sftp()
            with sftp.open(target, "r") as fh:
                return fh.read().decode("utf-8")
        finally:
            client.close()

    def write(self, rel_path: str, content: str) -> None:
        target = self._resolve(rel_path)
        client = self._connect()
        try:
            sftp = client.open_sftp()
            with sftp.open(target, "w") as fh:
                fh.write(content)
        finally:
            client.close()

    def delete(self, rel_path: str) -> None:
        target = self._resolve(rel_path)
        client = self._connect()
        try:
            sftp = client.open_sftp()
            sftp.remove(target)
        finally:
            client.close()


def get_backend(settings: Settings) -> FileBackend | None:
    backend = settings.files_backend
    if backend in ("", "none"):
        return None
    if backend == "local":
        if not settings.config_dir:
            raise FilesDisabledError("HA_CONFIG_DIR is required for the local backend.")
        return LocalBackend(settings.config_dir)
    if backend == "ssh":
        return SSHBackend(settings)
    raise FilesDisabledError(f"Unknown HA_FILES_BACKEND: {backend!r} (expected none/local/ssh)")
