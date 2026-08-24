"""Exact allowlisted file/directory removal with hash snapshots."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from .safety import ensure_windows, safe_child, validate_component


class WindowsFileCleaner:
    def __init__(self, allowed_roots: dict[str, str | Path] | None = None):
        self.allowed_roots = {str(name): Path(path).resolve() for name, path in (allowed_roots or {}).items()}

    def _target(self, component: dict[str, Any]) -> Path:
        component = validate_component(component)
        if component.get("type", component.get("component_type")) not in {"desktop_app", "process"}:
            raise ValueError("file cleaner accepts only desktop_app or process components")
        root_name = str(component.get("metadata", {}).get("allowed_root", ""))
        if root_name not in self.allowed_roots:
            raise ValueError("component has no configured explicit allowlisted root")
        return safe_child(str(component.get("path", "")), self.allowed_roots[root_name])

    @staticmethod
    def _hash(path: Path) -> str:
        digest = hashlib.sha256()
        if path.is_file():
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        return digest.hexdigest()

    def snapshot(self, component: dict[str, Any]) -> dict[str, Any]:
        ensure_windows()
        path = self._target(component)
        if not path.exists():
            raise FileNotFoundError(path)
        stat = path.stat()
        return {"path": str(path), "is_dir": path.is_dir(), "sha256": self._hash(path), "mtime_ns": stat.st_mtime_ns, "size": stat.st_size}

    def remove_component(self, component: dict[str, Any]) -> None:
        self.snapshot(component)
        path = self._target(component)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    def verify_absent(self, component: dict[str, Any]) -> bool:
        return not self._target(component).exists()
