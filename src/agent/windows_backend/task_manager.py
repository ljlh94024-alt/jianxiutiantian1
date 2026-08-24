"""Exact Task Scheduler COM adapter; it never invokes cmd, PowerShell or schtasks."""

from __future__ import annotations

from typing import Any

from .safety import ensure_windows, validate_component


class WindowsTaskManager:
    def _service(self):
        ensure_windows()
        try:
            import win32com.client  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("pywin32 Task Scheduler adapter is required on the target Agent") from exc
        service = win32com.client.Dispatch("Schedule.Service")
        service.Connect()
        return service

    @staticmethod
    def _parts(name: str) -> tuple[str, str]:
        normalized = name.replace("/", "\\")
        folder, _, leaf = normalized.rpartition("\\")
        return folder or "\\", leaf or normalized

    def _task(self, name: str):
        service = self._service()
        folder_name, leaf = self._parts(name)
        folder = service.GetFolder(folder_name)
        return service, folder, leaf, folder.GetTask(leaf)

    @staticmethod
    def _matches(task, component: dict[str, Any]) -> bool:
        definition = task.Definition
        creator = str(component.get("creator", "")).strip().casefold()
        author = str(getattr(definition.RegistrationInfo, "Author", "") or "").casefold()
        executable = str(component.get("path", "")).strip().casefold()
        xml = str(task.Xml).casefold()
        return (not creator or creator in author or creator in xml) and (not executable or executable in xml)

    def snapshot(self, component: dict[str, Any]) -> dict[str, Any]:
        component = validate_component(component)
        if component.get("type", component.get("component_type")) != "scheduled_task":
            raise ValueError("task manager only accepts scheduled_task components")
        _, _, _, task = self._task(component["name"])
        if not self._matches(task, component):
            raise ValueError("task creator or executable path does not match the requested component")
        return {"name": component["name"], "xml": str(task.Xml), "enabled": bool(task.Enabled), "state": int(task.State)}

    def remove_task(self, component: dict[str, Any]) -> None:
        snapshot = self.snapshot(component)
        _, folder, leaf, _ = self._task(component["name"])
        folder.DeleteTask(leaf, 0)

    def restore_task(self, snapshot: dict[str, Any]) -> None:
        ensure_windows()
        service = self._service()
        folder_name, leaf = self._parts(str(snapshot["name"]))
        folder = service.GetFolder(folder_name)
        # TASK_CREATE_OR_UPDATE=6, TASK_LOGON_INTERACTIVE_TOKEN=3.
        folder.RegisterTask(leaf, str(snapshot["xml"]), 6, None, None, 3, None)
        task = folder.GetTask(leaf)
        task.Enabled = bool(snapshot.get("enabled", True))

    def verify_absent(self, component: dict[str, Any]) -> bool:
        try:
            self._task(str(component["name"]))
        except Exception:
            return True
        return False
