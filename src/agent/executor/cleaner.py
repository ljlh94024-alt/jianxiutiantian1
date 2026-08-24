"""Input-method promotion cleanup without touching the input-method主体."""

from __future__ import annotations

from typing import Any, Protocol

from .safety import SafetyError, SafetyGate, SoftwareExecutionRequest


class CleanupBackend(Protocol):
    def disable_promotion_startup(self, software: str) -> None: ...
    def disable_promotion_service(self, software: str) -> None: ...
    def close_promotion_notifications(self, software: str) -> None: ...
    def clear_promotion_cache(self, software: str) -> None: ...


class InputMethodCleaner:
    OPERATIONS = ("disable_promotion_startup", "disable_promotion_service", "close_promotion_notifications", "clear_promotion_cache")

    def __init__(self, gate: SafetyGate, backend: CleanupBackend | None = None):
        self.gate = gate
        self.backend = backend

    def optimize(self, request: SoftwareExecutionRequest, execute: bool = False) -> dict[str, Any]:
        try:
            self.gate.validate(request)
        except SafetyError as exc:
            return {"status": "failed", "reason": str(exc)}
        if request.operation != "optimize_input_method":
            raise ValueError("Cleaner only accepts optimize_input_method")
        if not execute or self.backend is None:
            return {"status": "ready", "software": request.software, "operations": list(self.OPERATIONS), "dry_run": True}
        completed = []
        for operation in self.OPERATIONS:
            getattr(self.backend, operation)(request.software)
            completed.append(operation)
        return {"status": "success", "software": request.software, "operations": completed}
