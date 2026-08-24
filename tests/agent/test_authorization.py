import json

import pytest

from src.agent.audit import AuditLogger
from src.agent.client import AgentClient, AgentSecurityError, TargetIdentity
from src.agent.executor import WhitelistExecutor
from src.authorization.consent import AuthorizationRecord
from src.authorization.permission import PermissionLevel
from src.controller.task_sender import TaskPackageError, TaskSender


TARGET_ID = "PC001"


class Consent:
    def __init__(self, approved=True, mutate=None):
        self.approved = approved
        self.mutate = mutate or {}

    def request_consent(self, task, session_id, permission):
        values = {
            "target_id": task.target_id,
            "task_id": task.task_id,
            "session_id": session_id,
            "user_confirm": self.approved,
            "operator": "target_user",
            "time": "2026-08-24T00:00:00+08:00",
            "permission": permission,
        }
        values.update(self.mutate)
        return AuthorizationRecord(**values)


class PermissionRecorder:
    def __init__(self, granted):
        self.granted = granted
        self.requests = []

    def request_permission(self, task, required):
        self.requests.append((task.task_id, required))
        return self.granted


@pytest.fixture
def identity():
    return TargetIdentity.from_dict(
        {
            "target_id": TARGET_ID,
            "computer_name": "DESKTOP001",
            "hardware_id": "hardware-test-id",
            "created_time": "2026-08-24",
        }
    )


def _client(tmp_path, identity, handlers=None, permissions=None):
    return AgentClient(
        identity,
        WhitelistExecutor(handlers),
        AuditLogger(tmp_path / "logs"),
        permissions=permissions,
    )


def test_a0_scan_needs_consent_but_not_admin(tmp_path, identity):
    calls = []
    permissions = PermissionRecorder(True)
    client = _client(
        tmp_path, identity,
        {"scan": lambda task: calls.append(task.task_id) or {"status": "completed", "count": 3}},
        permissions,
    )
    task = TaskSender().create(TARGET_ID, "scan_001", "scan")
    result = client.process(task, Consent(True))
    assert (result.status, result.permission, calls) == ("completed", "A0", ["scan_001"])
    assert permissions.requests == [("scan_001", PermissionLevel.A0)]


def test_admin_task_requests_permission_and_stops_when_not_granted(tmp_path, identity):
    calls = []
    permissions = PermissionRecorder(False)
    client = _client(
        tmp_path, identity,
        {"approved_action": lambda task: calls.append(task.task_id) or {"status": "completed"}},
        permissions,
    )
    task = TaskSender().create(TARGET_ID, "admin_001", "approved_action", "L1", True)
    result = client.process(task, Consent(True))
    assert result.status == "permission_denied"
    assert calls == []
    assert permissions.requests == [("admin_001", PermissionLevel.A1)]


def test_l2_task_requests_second_level_permission(tmp_path, identity):
    permissions = PermissionRecorder(False)
    client = _client(tmp_path, identity, permissions=permissions)
    task = TaskSender().create(TARGET_ID, "risk_001", "approved_action", "L2", True)
    client.process(task, Consent(True))
    assert permissions.requests == [("risk_001", PermissionLevel.A2)]


def test_user_rejection_stops_before_permission_and_execution(tmp_path, identity):
    calls = []
    permissions = PermissionRecorder(True)
    client = _client(
        tmp_path, identity,
        {"scan": lambda task: calls.append(task.task_id) or {"status": "completed"}},
        permissions,
    )
    result = client.process(TaskSender().create(TARGET_ID, "scan_002", "scan"), Consent(False))
    assert result.status == "denied"
    assert calls == []
    assert permissions.requests == []


def test_wrong_target_is_rejected_and_logged(tmp_path, identity):
    client = _client(tmp_path, identity)
    with pytest.raises(AgentSecurityError, match="target_id"):
        client.process(TaskSender().create("PC999", "scan_003", "scan"), Consent(True))
    log = (tmp_path / "logs" / "session.log").read_text(encoding="utf-8")
    assert "target_rejected" in log


def test_authorization_must_bind_exact_session(tmp_path, identity):
    client = _client(tmp_path, identity)
    with pytest.raises(AgentSecurityError, match="not bound"):
        client.process(
            TaskSender().create(TARGET_ID, "scan_004", "scan"),
            Consent(True, {"session_id": "replayed-session"}),
        )


def test_all_three_audit_logs_are_written(tmp_path, identity):
    client = _client(
        tmp_path, identity,
        {"report": lambda task: {"status": "completed"}},
        PermissionRecorder(True),
    )
    client.process(TaskSender().create(TARGET_ID, "report_001", "report"), Consent(True))
    for filename in ("session.log", "authorization.log", "execution.log"):
        lines = (tmp_path / "logs" / filename).read_text(encoding="utf-8").splitlines()
        assert lines and all(json.loads(line)["time"] for line in lines)


@pytest.mark.parametrize("action", ["delete_all", "format", "disable_security", "hidden_execute"])
def test_forbidden_actions_cannot_enter_protocol(action):
    with pytest.raises(TaskPackageError, match="not allowed"):
        TaskSender().create(TARGET_ID, "bad_001", action)  # type: ignore[arg-type]


def test_l2_cannot_underdeclare_admin_requirement():
    with pytest.raises(TaskPackageError, match="must declare"):
        TaskSender().create(TARGET_ID, "bad_002", "approved_action", "L2", False)


def test_task_identity_fields_cannot_be_empty():
    with pytest.raises(TaskPackageError, match="cannot be empty"):
        TaskSender().create("", "task", "scan")
