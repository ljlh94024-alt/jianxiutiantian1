"""Exact HKCU Run and Startup-folder operations; no broad registry edits."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .safety import ensure_windows, safe_child, validate_component


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


class WindowsStartupManager:
    def _registry(self, component: dict[str, Any]) -> bool:
        return str(component.get("source", "")).casefold().endswith("currentversion\\run")

    def _startup_roots(self) -> tuple[Path, ...]:
        return (Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup", Path(os.environ.get("PROGRAMDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup")

    def snapshot(self, component: dict[str, Any]) -> dict[str, Any]:
        component = validate_component(component)
        if component.get("type", component.get("component_type")) != "startup":
            raise ValueError("startup manager only accepts startup components")
        ensure_windows()
        if self._registry(component):
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, access=winreg.KEY_READ) as key:
                value, kind = winreg.QueryValueEx(key, component["name"])
            return {"kind": "registry", "hive": "HKCU", "key": RUN_KEY, "name": component["name"], "value": value, "value_type": kind}
        path = Path(str(component.get("path", ""))).resolve()
        root = next((root for root in self._startup_roots() if root.is_dir() and (path == root or root.resolve() in path.parents)), None)
        if root is None:
            raise ValueError("startup path is outside the allowed Startup folders")
        return {"kind": "folder", "path": str(path), "exists": path.exists()}

    def disable_startup(self, component: dict[str, Any]) -> None:
        snapshot = self.snapshot(component)
        if snapshot["kind"] == "registry":
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, component["name"])
            return
        path = Path(snapshot["path"])
        if path.exists():
            path.rename(Path(str(path) + ".disabled"))

    def restore_startup(self, snapshot: dict[str, Any]) -> None:
        ensure_windows()
        if snapshot["kind"] == "registry":
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, snapshot["name"], 0, int(snapshot.get("value_type", winreg.REG_SZ)), snapshot["value"])
            return
        original = Path(snapshot["path"])
        disabled = Path(str(original) + ".disabled")
        if disabled.exists() and not original.exists():
            disabled.rename(original)

    def verify_disabled(self, component: dict[str, Any]) -> bool:
        if not self._registry(component):
            path = Path(str(component.get("path", ""))).resolve()
            return not path.exists() and Path(str(path) + ".disabled").exists()
        try:
            self.snapshot(component)
        except (FileNotFoundError, OSError):
            return True
        return False
