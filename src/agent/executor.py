"""Handler-based executor with no shell, elevation, or persistence features."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.controller.task_sender import ALLOWED_ACTIONS, TaskPackage


TaskHandler = Callable[[TaskPackage], dict[str, Any]]


class WhitelistExecutor:
    """Dispatch only explicitly registered handlers for protocol-whitelisted actions."""

    def __init__(self, handlers: dict[str, TaskHandler] | None = None):
        self._handlers = dict(handlers or {})
        unknown = set(self._handlers).difference(ALLOWED_ACTIONS)
        if unknown:
            raise ValueError(f"Handlers use non-whitelisted actions: {sorted(unknown)}")

    def execute(self, task: TaskPackage) -> dict[str, Any]:
        handler = self._handlers.get(task.action)
        if handler is None:
            return {
                "status": "not_implemented",
                "message": "No handler is registered; system execution is reserved for Task 007.",
            }
        result = handler(task)
        if not isinstance(result, dict):
            raise TypeError("Task handlers must return a result object")
        return result

