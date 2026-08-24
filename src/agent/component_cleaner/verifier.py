"""Post-cleanup verification through a read-only injected backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import ComponentPlan


class ComponentVerificationBackend(Protocol):
    def verify(self, plan: ComponentPlan) -> bool: ...


@dataclass(frozen=True)
class ComponentVerificationResult:
    status: str
    component: str
    checks: tuple[str, ...]
    reason: str = ""


class ComponentVerifier:
    def __init__(self, backend: ComponentVerificationBackend | None = None):
        self.backend = backend

    def verify(self, plan: ComponentPlan) -> ComponentVerificationResult:
        checks = {
            "service": ("service_stopped",),
            "startup": ("startup_entry_absent",),
            "scheduled_task": ("scheduled_task_absent",),
            "desktop_app": ("component_absent",),
            "process": ("process_absent",),
        }[plan.component.component_type]
        if self.backend is None:
            return ComponentVerificationResult("unavailable", plan.component.name, checks, "Verification backend is not configured")
        return ComponentVerificationResult("success" if self.backend.verify(plan) else "failed", plan.component.name, checks)

