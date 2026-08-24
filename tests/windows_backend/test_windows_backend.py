from pathlib import Path

from src.agent.component_cleaner.matcher import ComponentRuleSet
from src.agent.component_cleaner.planner import ComponentPlanner
from src.agent.windows_backend import (
    SnapshotStore,
    WindowsComponentTaskHandler,
    WindowsExecutionBackend,
    WindowsExecutionEngine,
)
from src.agent.windows_backend.safety import WindowsBackendSafetyError, safe_child
from src.agent.windows_backend.verifier import WindowsExecutionVerifier


class FakeManager:
    def __init__(self):
        self.calls = []

    def snapshot(self, component):
        self.calls.append(("snapshot", component["name"]))
        return {"name": component["name"], "state": "running", "startup_type": 2}

    def disable_service(self, component): self.calls.append(("disable_service", component["name"]))
    def disable_startup(self, component): self.calls.append(("disable_startup", component["name"]))
    def remove_task(self, component): self.calls.append(("remove_task", component["name"]))
    def remove_component(self, component): self.calls.append(("remove_component", component["name"]))
    def restore_service(self, state): self.calls.append(("restore_service", state["name"]))
    def restore_startup(self, state): self.calls.append(("restore_startup", state["name"]))
    def restore_task(self, state): self.calls.append(("restore_task", state["name"]))
    def verify_disabled(self, component): return True
    def verify_absent(self, component): return True


def _engine(tmp_path):
    manager = FakeManager()
    backend = WindowsExecutionBackend(manager, manager, manager, manager)
    verifier = WindowsExecutionVerifier(manager, manager, manager, manager)
    return WindowsExecutionEngine("PC001", backend, SnapshotStore(tmp_path / "backup"), verifier), manager


def test_real_engine_snapshots_verifies_and_can_roll_back(tmp_path):
    engine, manager = _engine(tmp_path)
    rules = ComponentRuleSet.load("rules/component_behavior")
    plan = ComponentPlanner(rules).plan([{"name": "2345UpdateService", "type": "service", "publisher": "2345"}], "PC001")[0]
    result = engine.execute("task-1", plan, authorized=True, human_confirmed=True, dry_run=False)
    assert result["status"] == "success"
    assert result["snapshot_id"]
    assert (tmp_path / "backup" / "PC001").is_dir()
    restored = engine.rollback(result["snapshot_id"], authorized=True, human_confirmed=True, target_id="PC001")
    assert restored["status"] == "success"
    assert ("restore_service", "2345UpdateService") in manager.calls


def test_engine_dry_run_does_not_call_backend(tmp_path):
    engine, manager = _engine(tmp_path)
    rules = ComponentRuleSet.load("rules/component_behavior")
    plan = ComponentPlanner(rules).plan([{"name": "2345UpdateService", "type": "service"}], "PC001")[0]
    assert engine.execute("task-2", plan, True, True, dry_run=True)["status"] == "ready"
    assert manager.calls == []
    assert not (tmp_path / "backup").exists()


def test_handler_requires_target_bound_rollback_and_rule_match(tmp_path):
    engine, _ = _engine(tmp_path)
    handler = WindowsComponentTaskHandler(ComponentRuleSet.load("rules/component_behavior"), engine)
    task = type("Task", (), {"task_id": "task-3", "target_id": "PC001", "parameters": {"component": {"name": "2345UpdateService", "type": "service"}, "matched_rule": "wrong"}})()
    assert handler.run(task, authorized=True)["reason"] == "component_rule_mismatch"


def test_protected_component_is_rejected_before_native_backend(tmp_path):
    engine, manager = _engine(tmp_path)
    rules = ComponentRuleSet.load("rules/component_behavior")
    plan = ComponentPlanner(rules).plan([{"name": "WPSUpdateService", "type": "service", "publisher": "Microsoft"}], "PC001")[0]
    assert engine.execute("task-4", plan, True, True, dry_run=False)["status"] == "blocked"
    assert manager.calls == []


def test_path_allowlist_rejects_escape(tmp_path):
    try:
        safe_child(tmp_path.parent, tmp_path)
    except WindowsBackendSafetyError:
        pass
    else:
        raise AssertionError("path escape must be rejected")
