"""Read-only component scanners with injectable providers for safe testing."""

from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol

from .models import Component


class ServiceProvider(Protocol):
    def services(self) -> Iterable[dict[str, Any]]: ...


class StartupProvider(Protocol):
    def startup_entries(self) -> Iterable[dict[str, Any]]: ...


class ScheduledTaskProvider(Protocol):
    def scheduled_tasks(self) -> Iterable[dict[str, Any]]: ...


class ProcessProvider(Protocol):
    def processes(self) -> Iterable[dict[str, Any]]: ...


class ComponentScanner:
    """Normalize provider snapshots; it performs no writes or process control."""

    def __init__(self, target_id: str, providers: Iterable[object] = ()):
        self.target_id = target_id
        self.providers = tuple(providers)

    def scan(self) -> list[dict[str, Any]]:
        components: list[dict[str, Any]] = []
        for provider in self.providers:
            for method_name in ("services", "startup_entries", "scheduled_tasks", "processes"):
                method = getattr(provider, method_name, None)
                if not callable(method):
                    continue
                type_name = {
                    "services": "service", "startup_entries": "startup", "scheduled_tasks": "scheduled_task", "processes": "process",
                }[method_name]
                for item in method() or ():
                    record = dict(item)
                    record.setdefault("type", type_name)
                    components.append(Component.from_dict(record, self.target_id).to_dict())
        return components


class WindowsComponentScanner:
    """Best-effort, read-only Windows snapshot using standard query surfaces."""

    def __init__(self, target_id: str):
        self.target_id = target_id

    def scan(self) -> list[dict[str, Any]]:
        if sys.platform != "win32":
            return []
        records = []
        records.extend(self._services())
        records.extend(self._scheduled_tasks())
        records.extend(self._startup_registry())
        records.extend(self._startup_folder())
        records.extend(self._processes())
        return records

    def _query(self, command: list[str]) -> str:
        result = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603
        return result.stdout if result.returncode == 0 else ""

    def _services(self) -> list[dict[str, Any]]:
        # sc.exe queryex is read-only; detailed executable paths are queried per service.
        text = self._query(["sc.exe", "query", "type=", "service", "state=", "all"])
        records = []
        for line in text.splitlines():
            if "SERVICE_NAME:" not in line:
                continue
            name = line.split(":", 1)[1].strip()
            detail = self._query(["sc.exe", "qc", name])
            path = next((item.split(":", 1)[1].strip() for item in detail.splitlines() if "BINARY_PATH_NAME" in item), "")
            records.append(Component.from_dict({"name": name, "type": "service", "path": path, "source": "ServiceManager"}, self.target_id).to_dict())
        return records

    def _scheduled_tasks(self) -> list[dict[str, Any]]:
        text = self._query(["schtasks.exe", "/Query", "/FO", "CSV", "/V", "/NH"])
        records = []
        for row in csv.reader(io.StringIO(text)):
            if not row or len(row) < 9:
                continue
            records.append(Component.from_dict({"name": row[0], "type": "scheduled_task", "path": row[8], "creator": row[6], "source": "TaskScheduler"}, self.target_id).to_dict())
        return records

    def _startup_registry(self) -> list[dict[str, Any]]:
        import winreg

        records = []
        locations = ((winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"), (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"))
        for hive, location in locations:
            try:
                with winreg.OpenKey(hive, location, access=winreg.KEY_READ) as key:
                    for index in range(winreg.QueryInfoKey(key)[1]):
                        name, value, _ = winreg.EnumValue(key, index)
                        records.append(Component.from_dict({"name": name, "type": "startup", "path": str(value), "source": location}, self.target_id).to_dict())
            except OSError:
                continue
        return records

    def _startup_folder(self) -> list[dict[str, Any]]:
        records = []
        folder = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"
        if folder.is_dir():
            records.extend(Component.from_dict({"name": item.name, "type": "startup", "path": str(item), "source": "StartupFolder"}, self.target_id).to_dict() for item in folder.iterdir())
        return records

    def _processes(self) -> list[dict[str, Any]]:
        text = self._query(["tasklist.exe", "/FO", "CSV", "/NH"])
        return [Component.from_dict({"name": row[0], "type": "process", "source": "ProcessSnapshot"}, self.target_id).to_dict() for row in csv.reader(io.StringIO(text)) if row]
