"""Read-only post-action verifier over fixed Windows managers."""

from __future__ import annotations

from typing import Any


class WindowsExecutionVerifier:
    def __init__(self, service_manager=None, startup_manager=None, task_manager=None, file_cleaner=None):
        self.service_manager = service_manager
        self.startup_manager = startup_manager
        self.task_manager = task_manager
        self.file_cleaner = file_cleaner

    def verify(self, action: str, component: dict[str, Any]) -> bool:
        if action == "disable_service" and self.service_manager:
            return bool(self.service_manager.verify_disabled(component))
        if action == "disable_startup" and self.startup_manager:
            return bool(self.startup_manager.verify_disabled(component))
        if action == "remove_task" and self.task_manager:
            return bool(self.task_manager.verify_absent(component))
        if action == "remove_component" and self.file_cleaner:
            return bool(self.file_cleaner.verify_absent(component))
        return False
