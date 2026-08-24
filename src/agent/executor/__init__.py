"""Task005 dispatch plus Task007 safety-gated software execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.controller.task_sender import ALLOWED_ACTIONS, TaskPackage

from .cleaner import InputMethodCleaner
from .engine import SafeSoftwareExecutor, SafeSoftwareTaskHandler
from .installer import Installer, PackageCatalog
from .safety import SafetyGate, SoftwareExecutionRequest
from .uninstaller import Uninstaller
from .verifier import VerificationResult, Verifier
from src.agent.windows_backend import WindowsComponentTaskHandler, WindowsExecutionBackend, WindowsExecutionEngine

TaskHandler = Callable[[TaskPackage], dict[str, Any]]


class WhitelistExecutor:
    """Dispatch only explicitly registered Task005 handlers."""

    def __init__(self, handlers: dict[str, TaskHandler] | None = None):
        self._handlers = dict(handlers or {})
        unknown = set(self._handlers).difference(ALLOWED_ACTIONS)
        if unknown:
            raise ValueError(f"Handlers use non-whitelisted actions: {sorted(unknown)}")

    def execute(self, task: TaskPackage, authorized: bool = False) -> dict[str, Any]:
        handler = self._handlers.get(task.action)
        if handler is None:
            return {"status": "not_implemented", "message": "No handler is registered; see Task 007."}
        if getattr(handler, "requires_authorization", False) and not authorized:
            return {"status": "authorization_required", "message": "Handler requires the completed Task005 consent handshake."}
        run = getattr(handler, "run", None)
        result = run(task, authorized) if callable(run) else handler(task)
        if not isinstance(result, dict):
            raise TypeError("Task handlers must return a result object")
        return result


__all__ = [
    "InputMethodCleaner", "Installer", "PackageCatalog", "SafeSoftwareExecutor", "SafeSoftwareTaskHandler", "SafetyGate",
    "SoftwareExecutionRequest", "Uninstaller", "VerificationResult", "Verifier",
    "WhitelistExecutor", "WindowsComponentTaskHandler", "WindowsExecutionBackend", "WindowsExecutionEngine",
]
