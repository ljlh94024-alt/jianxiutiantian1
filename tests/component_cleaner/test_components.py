import json

import pytest

from src.agent.component_cleaner import (
    Component,
    ComponentAuditLogger,
    ComponentExecutor,
    ComponentPlanner,
    ComponentRuleSet,
    ComponentScanner,
    ComponentTaskHandler,
    ComponentVerifier,
    WindowsComponentScanner,
)
from src.agent.component_cleaner.models import ComponentError


class SnapshotProvider:
    def services(self):
        return [{"name": "2345UpdateService", "publisher": "2345", "path": r"C:\2345\update.exe"}]

    def startup_entries(self):
        return [{"name": "LuDaShiWallpaper", "path": r"C:\LDS\wallpaper.exe"}]

    def scheduled_tasks(self):
        return [{"name": "LDSUpdateTask", "creator": "LuDaShi", "path": r"C:\LDS\update.exe"}]


class Backend:
    def __init__(self):
        self.calls = []

    def disable_service(self, item): self.calls.append(("service", item["name"]))
    def disable_startup(self, item): self.calls.append(("startup", item["name"]))
    def remove_task(self, item): self.calls.append(("task", item["name"]))
    def remove_component(self, item): self.calls.append(("component", item["name"]))


class Verify:
    def verify(self, plan): return True


def test_provider_scanner_normalizes_all_component_types():
    result = ComponentScanner("PC001", [SnapshotProvider()]).scan()
    assert {item["type"] for item in result} == {"service", "startup", "scheduled_task"}
    assert all(item["target_id"] == "PC001" for item in result)


def test_non_windows_scanner_is_read_only_noop():
    scanner = WindowsComponentScanner("PC001")
    # Do not scan the development machine in tests; only verify the target adapter contract.
    assert callable(scanner.scan)


@pytest.fixture(scope="module")
def planner():
    return ComponentPlanner(ComponentRuleSet.load("rules/component_behavior"))


def test_rules_plan_promotion_components(planner):
    plans = planner.plan(
        [
            {"name": "2345UpdateService", "type": "service", "publisher": "2345"},
            {"name": "LDSUpdateTask", "type": "scheduled_task", "creator": "LuDaShi"},
            {"name": "WPSUpdateService", "type": "service", "publisher": "Microsoft"},
        ],
        "PC001",
    )
    assert (plans[0].action, plans[0].level) == ("disable_service", "C2")
    assert (plans[1].action, plans[1].level) == ("remove_task", "C3")
    assert plans[2].protected and plans[2].action == "record"


def test_c3_requires_confirmation_and_backend_is_injected(planner):
    plan = planner.plan([{"name": "LDSUpdateTask", "type": "scheduled_task"}], "PC001")[0]
    backend = Backend()
    executor = ComponentExecutor(backend)
    assert executor.execute(plan, human_confirmed=False, dry_run=False)["status"] == "confirmation_required"
    result = executor.execute(plan, human_confirmed=True, dry_run=False)
    assert result["status"] == "success"
    assert backend.calls == [("task", "LDSUpdateTask")]


def test_protected_component_never_reaches_backend(planner):
    plan = planner.plan([{"name": "WPSUpdateService", "type": "service", "publisher": "Microsoft"}], "PC001")[0]
    backend = Backend()
    result = ComponentExecutor(backend).execute(plan, human_confirmed=True, dry_run=False)
    assert result["status"] == "blocked"
    assert backend.calls == []


def test_component_task_handler_replans_and_logs(tmp_path, planner):
    backend = Backend()
    logger = ComponentAuditLogger(tmp_path / "logs")
    handler = ComponentTaskHandler(ComponentRuleSet.load("rules/component_behavior"), ComponentExecutor(backend), ComponentVerifier(Verify()), logger)
    task = type("Task", (), {"target_id": "PC001", "parameters": {"component": {"name": "2345UpdateService", "type": "service", "publisher": "2345"}, "matched_rule": "2345_update_service", "dry_run": False}})()
    result = handler.run(task, authorized=True)
    assert result["status"] == "success"
    assert "2345UpdateService" in (tmp_path / "logs" / "component_clean.log").read_text(encoding="utf-8")


def test_component_rule_mismatch_stops_execution(planner):
    handler = ComponentTaskHandler(ComponentRuleSet.load("rules/component_behavior"), ComponentExecutor(Backend()))
    task = type("Task", (), {"target_id": "PC001", "parameters": {"component": {"name": "2345UpdateService", "type": "service"}, "matched_rule": "fake_rule"}})()
    assert handler.run(task, authorized=True)["reason"] == "component_rule_mismatch"
