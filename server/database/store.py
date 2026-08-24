"""SQLite persistence for devices, software, tasks, artifacts, and audit logs."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MaintenanceStore:
    def __init__(self, path: str | Path = "maintenance.db"):
        self.path = str(path)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        parent = Path(self.path).parent
        if str(parent) not in {"", "."}:
            parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._connect() as db:
            db.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS devices (
                    machine_id TEXT PRIMARY KEY,
                    hostname TEXT NOT NULL,
                    os TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'offline',
                    last_seen TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS software (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'unknown',
                    risk TEXT NOT NULL DEFAULT 'S0',
                    protection TEXT NOT NULL DEFAULT 'P2',
                    recommendation TEXT,
                    profile_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(machine_id, name),
                    FOREIGN KEY(machine_id) REFERENCES devices(machine_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    target_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    require_admin INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    parameters_json TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(machine_id) REFERENCES devices(machine_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT,
                    task_id TEXT,
                    event TEXT NOT NULL,
                    result_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ai_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    endpoint TEXT NOT NULL,
                    api_key TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 100,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _decode(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    def register_device(self, payload: dict[str, Any]) -> dict[str, Any]:
        machine_id = str(payload.get("machine_id", "")).strip()
        hostname = str(payload.get("hostname", "")).strip()
        operating_system = str(payload.get("os", "")).strip()
        if not machine_id or not hostname or not operating_system:
            raise ValueError("machine_id, hostname and os are required")
        now = _now()
        metadata = payload.get("metadata", {})
        with self._lock, self._connect() as db:
            db.execute(
                """INSERT INTO devices(machine_id, hostname, os, status, last_seen, metadata_json, created_at, updated_at)
                VALUES(?, ?, ?, 'online', ?, ?, ?, ?)
                ON CONFLICT(machine_id) DO UPDATE SET hostname=excluded.hostname, os=excluded.os,
                status='online', last_seen=excluded.last_seen, metadata_json=excluded.metadata_json, updated_at=excluded.updated_at""",
                (machine_id, hostname, operating_system, now, json.dumps(metadata, ensure_ascii=False), now, now),
            )
        return self.get_device(machine_id) or {}

    def heartbeat(self, machine_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "UPDATE devices SET status=?, last_seen=?, updated_at=? WHERE machine_id=?",
                (str(payload.get("status", "online")), str(payload.get("time", now)), now, machine_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown device: {machine_id}")
        return self.get_device(machine_id) or {}

    def list_devices(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM devices ORDER BY hostname")]

    def get_device(self, machine_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as db:
            row = db.execute("SELECT * FROM devices WHERE machine_id=?", (machine_id,)).fetchone()
            device = self._decode(row)
            if device:
                device["software"] = [
                    dict(item)
                    for item in db.execute(
                        "SELECT name, category, risk, protection, recommendation, updated_at FROM software WHERE machine_id=? ORDER BY name",
                        (machine_id,),
                    )
                ]
            return device

    def save_artifact(self, machine_id: str, kind: str, payload: Any) -> dict[str, Any]:
        allowed = {"computer_profile", "software_inventory", "software_profile", "migration_plan"}
        if kind not in allowed:
            raise ValueError(f"Unsupported artifact kind: {kind}")
        now = _now()
        with self._lock, self._connect() as db:
            if not db.execute("SELECT 1 FROM devices WHERE machine_id=?", (machine_id,)).fetchone():
                raise KeyError(f"Unknown device: {machine_id}")
            db.execute(
                "INSERT INTO artifacts(machine_id, kind, payload_json, created_at) VALUES(?, ?, ?, ?)",
                (machine_id, kind, json.dumps(payload, ensure_ascii=False), now),
            )
            if kind == "software_profile" and isinstance(payload, list):
                for profile in payload:
                    if not isinstance(profile, dict) or not profile.get("name"):
                        continue
                    db.execute(
                        """INSERT INTO software(machine_id, name, category, risk, protection, recommendation, profile_json, updated_at)
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(machine_id, name) DO UPDATE SET category=excluded.category, risk=excluded.risk,
                        protection=excluded.protection, recommendation=excluded.recommendation, profile_json=excluded.profile_json,
                        updated_at=excluded.updated_at""",
                        (
                            machine_id,
                            str(profile["name"]),
                            str(profile.get("category", "unknown")),
                            str(profile.get("risk_level", "S0")),
                            str(profile.get("protection", "P2")),
                            profile.get("recommended_replacement"),
                            json.dumps(profile, ensure_ascii=False),
                            now,
                        ),
                    )
        return {"machine_id": machine_id, "kind": kind, "stored_at": now}

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        task_id = str(payload.get("task_id") or f"task_{uuid.uuid4().hex[:12]}")
        target_id = str(payload.get("target_id", "")).strip()
        action = str(payload.get("action", "")).strip()
        risk = str(payload.get("risk", "L0"))
        require_admin = bool(payload.get("require_admin", False))
        if not target_id or action not in {"scan", "analyze", "report", "approved_action"}:
            raise ValueError("target_id and a whitelisted action are required")
        if risk not in {"L0", "L1", "L2"}:
            raise ValueError("Invalid risk")
        if action in {"scan", "analyze", "report"} and require_admin:
            raise ValueError("Read-only actions cannot require admin")
        if risk == "L2" and not require_admin:
            raise ValueError("L2 tasks must require admin")
        now = _now()
        with self._lock, self._connect() as db:
            if not db.execute("SELECT 1 FROM devices WHERE machine_id=?", (target_id,)).fetchone():
                raise KeyError(f"Unknown target device: {target_id}")
            db.execute(
                "INSERT INTO tasks(task_id, target_id, action, risk, require_admin, parameters_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (task_id, target_id, action, risk, int(require_admin), json.dumps(payload.get("parameters", {}), ensure_ascii=False), now, now),
            )
        return self.get_task(task_id) or {}

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as db:
            row = self._decode(db.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone())
            if row:
                row["parameters"] = json.loads(row.pop("parameters_json"))
                result = row.pop("result_json")
                row["result"] = json.loads(result) if result else None
            return row

    def list_tasks(self, target_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock, self._connect() as db:
            query = "SELECT * FROM tasks"
            params: tuple[Any, ...] = ()
            if target_id:
                query += " WHERE target_id=?"
                params = (target_id,)
            query += " ORDER BY created_at DESC"
            rows = []
            for row in db.execute(query, params):
                item = dict(row)
                item["parameters"] = json.loads(item.pop("parameters_json"))
                result = item.pop("result_json")
                item["result"] = json.loads(result) if result else None
                rows.append(item)
            return rows

    def claim_tasks(self, machine_id: str) -> list[dict[str, Any]]:
        device = self.get_device(machine_id)
        if device is None:
            raise KeyError(f"Unknown device: {machine_id}")
        now = _now()
        with self._lock, self._connect() as db:
            rows = list(db.execute("SELECT * FROM tasks WHERE target_id=? AND status='pending' ORDER BY created_at", (machine_id,)))
            for row in rows:
                db.execute("UPDATE tasks SET status='running', updated_at=? WHERE task_id=? AND status='pending'", (now, row["task_id"]))
        return [self.get_task(row["task_id"]) for row in rows if self.get_task(row["task_id"])]

    def complete_task(self, machine_id: str, task_id: str, result: dict[str, Any]) -> dict[str, Any]:
        status = str(result.get("status", "success"))
        if status not in {"success", "failed", "denied", "permission_denied", "not_implemented"}:
            status = "failed"
        now = _now()
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "UPDATE tasks SET status=?, result_json=?, updated_at=? WHERE task_id=? AND target_id=?",
                ("success" if status == "success" else "failed", json.dumps(result, ensure_ascii=False), now, task_id, machine_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown task or target mismatch: {task_id}")
            db.execute(
                "INSERT INTO logs(machine_id, task_id, event, result_json, created_at) VALUES(?, ?, ?, ?, ?)",
                (machine_id, task_id, "task_completed", json.dumps(result, ensure_ascii=False), now),
            )
        return self.get_task(task_id) or {}

    def list_logs(self, machine_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock, self._connect() as db:
            if machine_id:
                rows = db.execute("SELECT * FROM logs WHERE machine_id=? ORDER BY created_at DESC", (machine_id,))
            else:
                rows = db.execute("SELECT * FROM logs ORDER BY created_at DESC")
            return [dict(row) for row in rows]

    def save_ai_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        endpoint = str(payload.get("endpoint", "")).strip()
        model = str(payload.get("model", "")).strip()
        if not name or not endpoint or not model:
            raise ValueError("name, endpoint and model are required")
        now = _now()
        with self._lock, self._connect() as db:
            db.execute(
                """INSERT INTO ai_configs(name, endpoint, api_key, model, priority, enabled, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET endpoint=excluded.endpoint, api_key=excluded.api_key, model=excluded.model,
                priority=excluded.priority, enabled=excluded.enabled, updated_at=excluded.updated_at""",
                (name, endpoint, str(payload.get("api_key", "")), model, int(payload.get("priority", 100)), int(bool(payload.get("enabled", False))), now, now),
            )
            row = self._decode(db.execute("SELECT id, name, endpoint, model, priority, enabled, created_at, updated_at, length(api_key) AS key_length FROM ai_configs WHERE name=?", (name,)).fetchone())
        return self._mask_ai(row or {})

    @staticmethod
    def _mask_ai(item: dict[str, Any]) -> dict[str, Any]:
        if item.get("key_length", 0):
            item["api_key"] = "***configured***"
        else:
            item["api_key"] = ""
        return item

    def list_ai_configs(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT id, name, endpoint, model, priority, enabled, created_at, updated_at, length(api_key) AS key_length FROM ai_configs ORDER BY priority, name")
            return [self._mask_ai(dict(row)) for row in rows]
