from server.database import MaintenanceStore


def test_store_keeps_artifacts_and_logs(tmp_path):
    store = MaintenanceStore(tmp_path / "db.sqlite")
    store.register_device({"machine_id": "PC1", "hostname": "D1", "os": "Windows10"})
    store.save_artifact("PC1", "computer_profile", {"memory": "16GB"})
    task = store.create_task({"target_id": "PC1", "action": "report", "risk": "L0", "require_admin": False})
    store.claim_tasks("PC1")
    store.complete_task("PC1", task["task_id"], {"status": "success", "count": 1})
    assert store.list_logs("PC1")[0]["event"] == "task_completed"

