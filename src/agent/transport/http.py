"""Polling transport; the target Agent never listens for inbound connections."""

from __future__ import annotations

import json
from collections.abc import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.agent.client import TargetIdentity


class AgentTransportError(ConnectionError):
    pass


class HttpAgentTransport:
    def __init__(self, base_url: str, identity: TargetIdentity, agent_token: str = "", timeout: float = 10.0):
        if not base_url.startswith("https://") and not base_url.startswith("http://127.0.0.1") and not base_url.startswith("http://localhost"):
            raise ValueError("Agent transport requires HTTPS; HTTP is allowed only for loopback development")
        self.base_url = base_url.rstrip("/")
        self.identity = identity
        self.agent_token = agent_token
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "X-Agent-Token": self.agent_token}
        request = Request(self.base_url + path, data=body if method != "GET" else None, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:  # nosec B310 - URL scheme is validated above
                decoded = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AgentTransportError(str(exc)) from exc
        if not isinstance(decoded, dict):
            raise AgentTransportError("Server response must be an object")
        return decoded

    def register(self, metadata: dict | None = None) -> dict:
        return self._request(
            "POST", "/api/agents/register",
            {"machine_id": self.identity.target_id, "hostname": self.identity.computer_name, "os": "unknown", "metadata": metadata or {}},
        )

    def heartbeat(self, status: str = "online") -> dict:
        return self._request("POST", f"/api/agents/{self.identity.target_id}/heartbeat", {"status": status})

    def upload(self, kind: str, payload: object) -> dict:
        return self._request("POST", f"/api/agents/{self.identity.target_id}/artifacts", {"kind": kind, "payload": payload})

    def poll_tasks(self) -> list[dict]:
        response = self._request("GET", f"/api/agents/{self.identity.target_id}/tasks")
        tasks = response.get("tasks", [])
        return tasks if isinstance(tasks, list) else []

    def submit_result(self, task_id: str, result: dict) -> dict:
        return self._request("POST", f"/api/agents/{self.identity.target_id}/tasks/{task_id}/result", result)

