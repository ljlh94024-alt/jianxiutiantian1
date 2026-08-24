import threading

from server.api import ApiApplication, MaintenanceHTTPServer
from server.database import MaintenanceStore
from src.agent.client import TargetIdentity
from src.agent.transport import HttpAgentTransport


def test_agent_transport_uses_client_initiated_polling(tmp_path):
    store = MaintenanceStore(tmp_path / "db.sqlite")
    app = ApiApplication(store)
    server = MaintenanceHTTPServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        identity = TargetIdentity("PC1", "DESKTOP1", "hardware-id", "2026-08-24")
        transport = HttpAgentTransport(f"http://127.0.0.1:{server.server_address[1]}", identity)
        assert transport.register()["machine_id"] == "PC1"
        task = store.create_task({"target_id": "PC1", "action": "report", "risk": "L0", "require_admin": False})
        tasks = transport.poll_tasks()
        assert tasks[0]["task_id"] == task["task_id"]
        assert transport.submit_result(task["task_id"], {"status": "success"})["status"] == "success"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

