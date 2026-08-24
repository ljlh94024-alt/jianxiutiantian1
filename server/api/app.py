"""Small standard-library HTTP API and dashboard host for local maintenance work."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from server.database import MaintenanceStore
from server.models import validate_device_payload, validate_task_payload


class ApiApplication:
    def __init__(self, store: MaintenanceStore, console_token: str = "", agent_token: str = "", dashboard_dir: str | Path | None = None):
        self.store = store
        self.console_token = console_token
        self.agent_token = agent_token
        self.dashboard_dir = Path(dashboard_dir or Path(__file__).resolve().parents[2] / "web" / "dashboard")

    def _authorized(self, headers: dict[str, str], agent: bool = False) -> bool:
        expected = self.agent_token if agent else self.console_token
        if not expected:
            return True
        supplied = headers.get("X-Agent-Token" if agent else "Authorization", "")
        if not agent and supplied.startswith("Bearer "):
            supplied = supplied[7:]
        return supplied == expected

    def dispatch(self, method: str, path: str, body: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
        body = body or {}
        headers = headers or {}
        parsed = urlparse(path)
        route = parsed.path.rstrip("/") or "/"
        try:
            if route == "/api/health" and method == "GET":
                return 200, {"status": "ok", "service": "maintenance-control-plane"}
            if route.startswith("/api/agents"):
                if not self._authorized(headers, agent=True):
                    return 401, {"error": "agent authorization required"}
                return self._agent(method, route, body)
            if route.startswith("/api/") and not self._authorized(headers):
                return 401, {"error": "console login required"}
            return self._console(method, route, body, parse_qs(parsed.query))
        except KeyError as exc:
            return 404, {"error": str(exc)}
        except (ValueError, json.JSONDecodeError) as exc:
            return 400, {"error": str(exc)}

    def _agent(self, method: str, route: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        parts = route.split("/")
        if route == "/api/agents/register" and method == "POST":
            validate_device_payload(body)
            return 201, self.store.register_device(body)
        if len(parts) >= 5:
            machine_id = parts[3]
            operation = parts[4]
            if operation == "heartbeat" and method == "POST":
                return 200, self.store.heartbeat(machine_id, body)
            if operation == "artifacts" and method == "POST":
                return 201, self.store.save_artifact(machine_id, str(body.get("kind", "")), body.get("payload"))
            if operation == "tasks" and method == "GET":
                return 200, {"tasks": self.store.claim_tasks(machine_id)}
            if operation == "tasks" and len(parts) == 7 and parts[6] == "result" and method == "POST":
                return 200, self.store.complete_task(machine_id, parts[5], body)
        return 404, {"error": "agent route not found"}

    def _console(self, method: str, route: str, body: dict[str, Any], query: dict[str, list[str]]) -> tuple[int, dict[str, Any]]:
        if route == "/api/devices" and method == "GET":
            return 200, {"devices": self.store.list_devices()}
        if route.startswith("/api/devices/") and method == "GET":
            return 200, self.store.get_device(route.split("/")[3]) or {}
        if route == "/api/tasks" and method == "GET":
            target_id = (query.get("target_id") or [None])[0]
            return 200, {"tasks": self.store.list_tasks(target_id)}
        if route == "/api/tasks" and method == "POST":
            validate_task_payload(body)
            return 201, self.store.create_task(body)
        if route == "/api/logs" and method == "GET":
            target_id = (query.get("target_id") or [None])[0]
            return 200, {"logs": self.store.list_logs(target_id)}
        if route == "/api/ai-configs" and method == "GET":
            return 200, {"configs": self.store.list_ai_configs()}
        if route == "/api/ai-configs" and method == "POST":
            return 201, self.store.save_ai_config(body)
        return 404, {"error": "console route not found"}


class _Handler(BaseHTTPRequestHandler):
    app: ApiApplication

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _handle_api(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        body = json.loads(raw.decode("utf-8")) if raw else {}
        status, payload = self.app.dispatch(self.command, self.path, body, dict(self.headers))
        self._send_json(status, payload)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            try:
                self._handle_api()
            except Exception as exc:  # boundary must not expose a traceback
                self._send_json(400, {"error": str(exc)})
            return
        relative = "index.html" if self.path in {"/", ""} else self.path.lstrip("/")
        candidate = (self.app.dashboard_dir / relative).resolve()
        if self.app.dashboard_dir.resolve() not in candidate.parents and candidate != self.app.dashboard_dir.resolve() / "index.html":
            self._send_json(404, {"error": "not found"})
            return
        if not candidate.is_file():
            self._send_json(404, {"error": "not found"})
            return
        content = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:  # noqa: N802
        try:
            self._handle_api()
        except Exception as exc:
            self._send_json(400, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return


class MaintenanceHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], app: ApiApplication):
        handler = type("MaintenanceHandler", (_Handler,), {"app": app})
        super().__init__(address, handler)
