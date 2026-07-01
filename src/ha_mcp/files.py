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
import threading
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
    """SFTP-backed file access with trust-on-first-use host key handling and a
    reused connection (one SSH handshake instead of one per file operation)."""

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
        self._client = None
        self._sftp = None
        self._lock = threading.Lock()

    def _open_client(self):
        import paramiko

        client = paramiko.SSHClient()
        # Trust-on-first-use: unknown hosts are accepted once and persisted to
        # a known_hosts file; a *changed* key on a later connection is rejected
        # (protects the SSH password/key against MITM after the first run).
        known_hosts = Path(self.s.ssh_known_hosts).expanduser()
        known_hosts.parent.mkdir(parents=True, exist_ok=True)
        if known_hosts.is_file():
            client.load_host_keys(str(known_hosts))
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
        try:
            client.save_host_keys(str(known_hosts))
        except OSError:
            pass  # persistence is best-effort; the connection itself is fine
        return client

    def _get_sftp(self):
        """Return a healthy cached SFTP session, reconnecting when stale."""
        if self._client is not None:
            transport = self._client.get_transport()
            if transport is not None and transport.is_active() and self._sftp is not None:
                return self._sftp
            self._close_locked()
        self._client = self._open_client()
        self._sftp = self._client.open_sftp()
        return self._sftp

    def _close_locked(self) -> None:
        if self._sftp is not None:
            try:
                self._sftp.close()
            except Exception:  # noqa: BLE001
                pass
            self._sftp = None
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass
            self._client = None

    def _resolve(self, rel_path: str) -> str:
        normalized = _normalize(rel_path)
        target = posixpath.normpath(posixpath.join(self.root, normalized))
        if target != self.root and not target.startswith(self.root + "/"):
            raise ValueError(f"Path escapes the config directory: {rel_path!r}")
        return target

    def list_dir(self, rel_path: str) -> list[FileEntry]:
        base = self._resolve(rel_path)
        with self._lock:
            sftp = self._get_sftp()
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

    def read(self, rel_path: str) -> str:
        target = self._resolve(rel_path)
        with self._lock:
            sftp = self._get_sftp()
            with sftp.open(target, "r") as fh:
                return fh.read().decode("utf-8")

    def write(self, rel_path: str, content: str) -> None:
        target = self._resolve(rel_path)
        with self._lock:
            sftp = self._get_sftp()
            with sftp.open(target, "w") as fh:
                fh.write(content)

    def delete(self, rel_path: str) -> None:
        target = self._resolve(rel_path)
        with self._lock:
            sftp = self._get_sftp()
            sftp.remove(target)


# One backend per process so the SSH backend can keep its connection alive
# across tool calls.
_cached_backend: FileBackend | None = None
_cache_lock = threading.Lock()


def get_backend(settings: Settings) -> FileBackend | None:
    backend = settings.files_backend
    if backend in ("", "none"):
        return None
    global _cached_backend
    with _cache_lock:
        if _cached_backend is not None:
            return _cached_backend
        if backend == "local":
            if not settings.config_dir:
                raise FilesDisabledError("HA_CONFIG_DIR is required for the local backend.")
            _cached_backend = LocalBackend(settings.config_dir)
        elif backend == "ssh":
            _cached_backend = SSHBackend(settings)
        else:
            raise FilesDisabledError(
                f"Unknown HA_FILES_BACKEND: {backend!r} (expected none/local/ssh)"
            )
        return _cached_backend
