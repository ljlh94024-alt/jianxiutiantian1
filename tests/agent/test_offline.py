import json

from src.agent.audit import AuditLogger
from src.agent.client import AgentClient, TargetIdentity
from src.agent.executor import WhitelistExecutor
from src.authorization.consent import AuthorizationRecord
from src.controller.task_sender import TaskSender
from main import create_task_package


class Approve:
    def request_consent(self, task, session_id, permission):
        return AuthorizationRecord.create(task, session_id, True, "target_user", permission)


def test_offline_task_and_result_round_trip(tmp_path):
    task_path = tmp_path / "task_package.json"
    result_path = tmp_path / "result_package.json"
    sender = TaskSender()
    sender.write_offline(sender.create("PC001", "analyze_001", "analyze"), task_path)
    client = AgentClient(
        TargetIdentity.from_dict(
            {"target_id": "PC001", "computer_name": "DESKTOP001", "hardware_id": "id", "created_time": "2026-08-24"}
        ),
        WhitelistExecutor({"analyze": lambda task: {"status": "completed", "suggestions": 2}}),
        AuditLogger(tmp_path / "logs"),
    )
    result = client.process_offline(task_path, result_path, Approve())
    written = json.loads(result_path.read_text(encoding="utf-8"))
    assert result.status == "completed"
    assert written["target_id"] == "PC001"
    assert written["result"]["suggestions"] == 2


def test_approved_action_has_no_default_system_executor(tmp_path):
    client = AgentClient(
        TargetIdentity.from_dict(
            {"target_id": "PC001", "computer_name": "DESKTOP001", "hardware_id": "id", "created_time": "2026-08-24"}
        ),
        WhitelistExecutor(),
        AuditLogger(tmp_path / "logs"),
    )
    task = TaskSender().create("PC001", "approved_001", "approved_action")
    result = client.process(task, Approve())
    assert result.status == "not_implemented"
    assert "Task 007" in result.result["message"]


def test_controller_cli_helper_generates_task_package(tmp_path):
    output = tmp_path / "task_package.json"
    assert create_task_package("PC001", "report_002", "report", "L0", False, output) == 0
    task = json.loads(output.read_text(encoding="utf-8"))
    assert task["target_id"] == "PC001"
    assert task["action"] == "report"
