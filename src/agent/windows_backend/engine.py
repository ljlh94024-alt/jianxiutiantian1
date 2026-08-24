"""Authorized, snapshotted and fail-stop execution orchestration."""

from __future__ import annotations

from typing import Any

from src.agent.component_cleaner.audit import ComponentAuditLogger
from src.agent.component_cleaner.matcher import ComponentRuleSet
from src.agent.component_cleaner.planner import ComponentPlanner
from src.agent.component_cleaner.models import ComponentPlan

from .rollback import RollbackManager
from .safety import WindowsBackendSafetyError, validate_component
from .snapshot import SnapshotStore
from .verifier import WindowsExecutionVerifier


class WindowsExecutionBackend:
    def __init__(self, service_manager, startup_manager, task_manager, file_cleaner):
        self.service_manager = service_manager
        self.startup_manager = startup_manager
        self.task_manager = task_manager
        self.file_cleaner = file_cleaner

    def snapshot(self, component: dict[str, Any]) -> dict[str, Any]:
        component_type = component.get("type", component.get("component_type"))
        manager = {"service": self.service_manager, "startup": self.startup_manager, "scheduled_task": self.task_manager, "desktop_app": self.file_cleaner, "process": self.file_cleaner}.get(component_type)
        if manager is None:
            raise WindowsBackendSafetyError("no fixed backend for component type")
        return manager.snapshot(component)

    def _manager(self, component: dict[str, Any]):
        component_type = component.get("type", component.get("component_type"))
        return {"service": self.service_manager, "startup": self.startup_manager, "scheduled_task": self.task_manager, "desktop_app": self.file_cleaner, "process": self.file_cleaner}.get(component_type)

    def disable_service(self, component):
        self.service_manager.disable_service(component)

    def disable_startup(self, component):
        self.startup_manager.disable_startup(component)

    def remove_task(self, component):
        self.task_manager.remove_task(component)

    def remove_component(self, component):
        self.file_cleaner.remove_component(component)

    def restore_service(self, state): self.service_manager.restore_service(state)
    def restore_startup(self, state): self.startup_manager.restore_startup(state)
    def restore_task(self, state): self.task_manager.restore_task(state)


class WindowsExecutionEngine:
    def __init__(self, target_id: str, backend: WindowsExecutionBackend, snapshots: SnapshotStore, verifier: WindowsExecutionVerifier, logger: ComponentAuditLogger | None = None):
        self.target_id, self.backend, self.snapshots, self.verifier, self.logger = target_id, backend, snapshots, verifier, logger
        self.rollback_manager = RollbackManager(snapshots, backend)

    def execute(self, task_id: str, plan: ComponentPlan, authorized: bool, human_confirmed: bool, dry_run: bool = True) -> dict[str, Any]:
        if plan.target_id != self.target_id:
            return {"status": "failed", "reason": "target_mismatch"}
        if not authorized:
            return {"status": "authorization_required"}
        if plan.protected:
            return {"status": "blocked", "reason": "protected_component"}
        if plan.action == "record":
            return {"status": "recorded", "component": plan.component.name}
        if not human_confirmed:
            return {"status": "confirmation_required"}
        try:
            component = validate_component(plan.component.to_dict(), self.target_id)
            if dry_run:
                return {"status": "ready", "action": plan.action, "component": plan.component.name, "dry_run": True}
            state = self.backend.snapshot(component)
            snapshot = self.snapshots.create(self.target_id, task_id, plan.action, component, state)
            getattr(self.backend, plan.action)(component)
            if not self.verifier.verify(plan.action, component):
                result = {"status": "failed", "reason": "verification_failed", "snapshot_id": snapshot["snapshot_id"]}
            else:
                result = {"status": "success", "action": plan.action, "component": plan.component.name, "snapshot_id": snapshot["snapshot_id"]}
            if self.logger:
                self.logger.record(plan.component.name, plan.component.component_type, plan.action, result["status"], snapshot_id=snapshot["snapshot_id"])
            return result
        except Exception as exc:
            if self.logger:
                self.logger.record(plan.component.name, plan.component.component_type, plan.action, "failed", error=str(exc))
            return {"status": "failed", "reason": "execution_error", "error": str(exc)}

    def rollback(self, snapshot_id: str, authorized: bool, human_confirmed: bool, target_id: str | None = None) -> dict[str, Any]:
        try:
            if target_id:
                snapshot = self.snapshots.load(snapshot_id)
                if snapshot.get("machine_id") != target_id:
                    return {"status": "failed", "reason": "target_mismatch"}
            return self.rollback_manager.rollback(snapshot_id, authorized, human_confirmed)
        except Exception as exc:
            return {"status": "failed", "reason": "rollback_error", "error": str(exc)}


class WindowsComponentTaskHandler:
    requires_authorization = True

    def __init__(self, rules: ComponentRuleSet, engine: WindowsExecutionEngine):
        self.planner, self.engine = ComponentPlanner(rules), engine

    def run(self, task, authorized: bool) -> dict[str, Any]:
        if not authorized:
            return {"status": "authorization_required"}
        params = task.parameters
        if str(params.get("operation", "")) == "rollback":
            return self.engine.rollback(str(params.get("snapshot_id", "")), True, True, task.target_id)
        component = params.get("component")
        if not isinstance(component, dict):
            return {"status": "failed", "reason": "component_payload_required"}
        plan = self.planner.plan([component], task.target_id)[0]
        if params.get("matched_rule") and params["matched_rule"] != plan.matched_rule:
            return {"status": "failed", "reason": "component_rule_mismatch"}
        return self.engine.execute(task.task_id, plan, True, True, bool(params.get("dry_run", True)))
