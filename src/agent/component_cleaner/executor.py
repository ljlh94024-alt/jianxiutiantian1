"""Execute only a matched component plan through an injected backend."""

from __future__ import annotations

from typing import Any, Protocol

from .models import ComponentPlan
from .audit import ComponentAuditLogger
from .matcher import ComponentRuleSet
from .planner import ComponentPlanner
from .verifier import ComponentVerifier


class ComponentBackend(Protocol):
    def disable_service(self, component: dict[str, Any]) -> None: ...
    def disable_startup(self, component: dict[str, Any]) -> None: ...
    def remove_task(self, component: dict[str, Any]) -> None: ...
    def remove_component(self, component: dict[str, Any]) -> None: ...


class ComponentExecutor:
    def __init__(self, backend: ComponentBackend | None = None):
        self.backend = backend

    def execute(self, plan: ComponentPlan, human_confirmed: bool = False, dry_run: bool = True) -> dict[str, Any]:
        if plan.protected:
            return {"status": "blocked", "reason": "protected_component", "component": plan.component.name}
        if plan.action == "record":
            return {"status": "recorded", "component": plan.component.name}
        if plan.confirm_required and not human_confirmed:
            return {"status": "confirmation_required", "component": plan.component.name}
        if not dry_run and self.backend is None:
            return {"status": "failed", "reason": "component_backend_not_configured"}
        if dry_run:
            return {"status": "ready", "action": plan.action, "component": plan.component.name, "dry_run": True}
        method_name = {
            "disable_service": "disable_service", "disable_startup": "disable_startup",
            "remove_task": "remove_task", "remove_component": "remove_component",
        }.get(plan.action)
        if method_name is None:
            return {"status": "failed", "reason": "unsupported_component_action"}
        getattr(self.backend, method_name)(plan.component.to_dict())
        return {"status": "success", "action": plan.action, "component": plan.component.name}


class ComponentTaskHandler:
    """Task005 adapter that re-plans the supplied component before execution."""

    requires_authorization = True

    def __init__(self, rules: ComponentRuleSet, executor: ComponentExecutor, verifier: ComponentVerifier | None = None, logger: ComponentAuditLogger | None = None):
        self.planner = ComponentPlanner(rules)
        self.executor = executor
        self.verifier = verifier or ComponentVerifier()
        self.logger = logger

    def run(self, task, authorized: bool) -> dict[str, Any]:
        if not authorized:
            return {"status": "authorization_required"}
        raw_component = task.parameters.get("component")
        if not isinstance(raw_component, dict):
            return {"status": "failed", "reason": "component_payload_required"}
        plans = self.planner.plan([raw_component], task.target_id)
        plan = plans[0]
        provided_rule = task.parameters.get("matched_rule")
        if provided_rule and provided_rule != plan.matched_rule:
            return {"status": "failed", "reason": "component_rule_mismatch"}
        result = self.executor.execute(plan, human_confirmed=True, dry_run=bool(task.parameters.get("dry_run", True)))
        if result.get("status") == "success":
            verification = self.verifier.verify(plan)
            result["verification"] = {"status": verification.status, "checks": list(verification.checks), "reason": verification.reason}
            if verification.status != "success":
                result["status"] = "failed"
        if self.logger:
            self.logger.record(plan.component.name, plan.component.component_type, plan.action, str(result.get("status")), level=plan.level)
        return result
