# Web Maintenance Console

Task 006 adds a small SQLite-backed control plane and a single-page dashboard. The HTTP API is deliberately narrow:

- `POST /api/agents/register`
- `POST /api/agents/{machine_id}/heartbeat`
- `POST /api/agents/{machine_id}/artifacts`
- `GET /api/agents/{machine_id}/tasks`
- `POST /api/agents/{machine_id}/tasks/{task_id}/result`
- `GET /api/devices` and `GET /api/devices/{machine_id}`
- `GET/POST /api/tasks`
- `GET /api/logs`
- `GET/POST /api/ai-configs`

Agent routes use `X-Agent-Token`; console routes use `Authorization: Bearer ...`. The default development server binds only loopback. A production deployment must put an authenticated TLS reverse proxy in front of it.

The database stores devices, software, tasks, artifacts, logs, and AI configurations. API keys are never returned in full by the API or dashboard. The dashboard only creates protocol-whitelisted task requests; it cannot invoke AI execution, remote Shell, delete, format, security disabling, or hidden actions.

