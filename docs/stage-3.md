# Stage 3: Local Server with Event Streaming & Preview API

## 1. Overview
Stage 3 establishes the server and real-time streaming bridge between the decentralized multi-agent swarm runtime and client interfaces (such as the upcoming Stage 4 React + Vite dashboard).

### Key Components:
1. **FastAPI REST API ([`api/server.py`](file:///D:/swarm technology/api/server.py))**:
   - `GET /health`: Server health check, active swarms count, and system uptime.
   - `POST /runs`: Spawns autonomous multi-agent swarm in background (`asyncio.create_task`).
   - `GET /runs`: Lists all historical and active runs with timestamps and goal prompts.
   - `GET /runs/{run_id}`: Full run inspectability (goal, blackboard tasks, artifacts, active signals, and QA report).
   - `GET /runs/{run_id}/events`: Incremental polling support (`?since_id=N`).
   - `GET /runs/{run_id}/preview/{path}`: Live sandbox web asset preview with proper MIME types (`text/html`, `text/css`, `application/javascript`) and canonical path traversal rejection (`SandboxSecurityViolation` -> 403).
2. **Starlette WebSocket Streaming (`/ws/runs/{run_id}`)**:
   - Streams past historical events upon connection.
   - Streams live incremental events as swarm agents claim tasks, edit files, and emit signals.
   - Streams periodic state snapshots every 2s (`tasks`, `signals`, `artifacts`, `status`).
3. **Server Launcher ([`api/run_server.py`](file:///D:/swarm technology/api/run_server.py))**:
   - Configurable host/port launcher with uvicorn.

---

## 2. API Specifications

### REST Endpoints
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Server heartbeat and active swarm count |
| `POST` | `/runs` | Launch new swarm run (`{"prompt": "...", "model": "qwen3.5:4b"}`) |
| `GET` | `/runs` | List all historical runs |
| `GET` | `/runs/{run_id}` | Detailed blackboard state, tasks, artifacts, signals, and QA audit |
| `GET` | `/runs/{run_id}/events` | Fetch event log entries with `since_id` cursor |
| `GET` | `/runs/{run_id}/preview/*` | Serve live sandboxed assets (`index.html`, `styles.css`, `script.js`) |

### WebSocket Protocol (`/ws/runs/{run_id}`)
- **Event Message**:
  ```json
  {
    "type": "event",
    "data": {
      "id": 12,
      "ts": 1794036218.4,
      "run_id": "run_1794036218",
      "agent_id": "agent-style-01",
      "event_type": "file_edit",
      "target": "styles.css",
      "payload": {"bytes": 7680, "summary": "Wrote dark theme CSS"}
    }
  }
  ```
- **State Snapshot Message**:
  ```json
  {
    "type": "state_snapshot",
    "data": {
      "status": "completed",
      "tasks": [...],
      "signals": [...],
      "artifacts": [...]
    }
  }
  ```

---

## 3. Verification & Acceptance Checks
All 32 test cases passed cleanly:
```
tests/test_api.py::test_health_endpoint PASSED                           [  3%]
tests/test_api.py::test_list_runs PASSED                                 [  6%]
tests/test_api.py::test_get_run_details PASSED                           [  9%]
tests/test_api.py::test_get_run_events_polling PASSED                    [ 12%]
tests/test_api.py::test_preview_html_asset PASSED                        [ 15%]
tests/test_api.py::test_preview_css_asset PASSED                         [ 18%]
tests/test_api.py::test_preview_js_asset PASSED                          [ 21%]
tests/test_api.py::test_preview_traversal_security_rejection PASSED      [ 25%]
tests/test_api.py::test_websocket_event_streaming PASSED                 [ 28%]
...
======================== 32 passed in 3.45s ========================
```

### Live Server Probing
Probed on `http://127.0.0.1:8000`:
- `HEALTH: 200`
- `RUNS LISTED: 9`
- `PREVIEW HTML STATUS: 200 (BYTES: 1885)`
- `WEBSOCKET: Connected & streaming verified`
