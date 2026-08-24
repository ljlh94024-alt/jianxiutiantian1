import json

from server.api import ApiApplication
from server.database import MaintenanceStore


MACHINE = "PC001"


def _app(tmp_path):
    return ApiApplication(MaintenanceStore(tmp_path / "maintenance.db"), console_token="console", agent_token="agent")


def agent(app, method, path, body=None):
    return app.dispatch(method, path, body or {}, {"X-Agent-Token": "agent"})


def console(app, method, path, body=None):
    return app.dispatch(method, path, body or {}, {"Authorization": "Bearer console"})


def test_agent_registration_heartbeat_and_console_device_view(tmp_path):
    app = _app(tmp_path)
    status, device = agent(app, "POST", "/api/agents/register", {"machine_id": MACHINE, "hostname": "DESKTOP001", "os": "Windows11"})
    assert (status, device["status"]) == (201, "online")
    status, _ = agent(app, "POST", f"/api/agents/{MACHINE}/heartbeat", {"status": "online"})
    assert status == 200
    status, data = console(app, "GET", "/api/devices")
    assert (status, data["devices"][0]["machine_id"]) == (200, MACHINE)


def test_upload_scan_result_populates_software_page(tmp_path):
    app = _app(tmp_path)
    agent(app, "POST", "/api/agents/register", {"machine_id": MACHINE, "hostname": "D", "os": "Windows11"})
    status, _ = agent(app, "POST", f"/api/agents/{MACHINE}/artifacts", {"kind": "software_profile", "payload": [{"name": "WPS Office", "category": "office", "risk_level": "S0", "protection": "P1"}]})
    assert status == 201
    _, device = console(app, "GET", f"/api/devices/{MACHINE}")
    assert device["software"][0]["protection"] == "P1"


def test_task_queue_claim_and_result(tmp_path):
    app = _app(tmp_path)
    agent(app, "POST", "/api/agents/register", {"machine_id": MACHINE, "hostname": "D", "os": "Windows11"})
    status, task = console(app, "POST", "/api/tasks", {"target_id": MACHINE, "action": "report", "risk": "L0", "require_admin": False})
    assert status == 201
    status, payload = agent(app, "GET", f"/api/agents/{MACHINE}/tasks")
    assert (status, payload["tasks"][0]["status"]) == (200, "running")
    status, completed = agent(app, "POST", f"/api/agents/{MACHINE}/tasks/{task['task_id']}/result", {"status": "success", "report": "ok"})
    assert (status, completed["status"]) == (200, "success")
    _, history = console(app, "GET", "/api/tasks")
    assert history["tasks"][0]["result"]["report"] == "ok"


def test_protected_api_requires_login_and_forbidden_task_rejected(tmp_path):
    app = _app(tmp_path)
    status, _ = app.dispatch("GET", "/api/devices", {}, {})
    assert status == 401
    status, error = console(app, "POST", "/api/tasks", {"target_id": MACHINE, "action": "delete_all"})
    assert status == 400 and "whitelisted" in error["error"]


def test_ai_config_is_saved_but_key_is_never_returned(tmp_path):
    app = _app(tmp_path)
    status, item = console(app, "POST", "/api/ai-configs", {"name": "backup", "endpoint": "https://api.example.test", "api_key": "secret-key", "model": "model-1", "enabled": True})
    assert status == 201
    assert item["api_key"] == "***configured***"
    _, listing = console(app, "GET", "/api/ai-configs")
    assert listing["configs"][0]["api_key"] == "***configured***"


def test_agent_token_is_separate_from_console_token(tmp_path):
    app = _app(tmp_path)
    status, _ = app.dispatch("POST", "/api/agents/register", {"machine_id": MACHINE, "hostname": "D", "os": "Windows"}, {"Authorization": "Bearer console"})
    assert status == 401

