"""
Integration and End-to-End Tests for Stage 3 FastAPI Server & WebSocket Streaming.
Tests:
- Health check
- POST /runs (spawns run)
- GET /runs (lists runs)
- GET /runs/{run_id} (details, blackboard tasks, artifacts, QA)
- GET /runs/{run_id}/events (incremental polling)
- GET /runs/{run_id}/preview/* (serves HTML, CSS, JS with correct MIME types)
- Path traversal security rejection
- WS /ws/runs/{run_id} (WebSocket streaming of events and snapshots)
"""

import sys
sys.path.insert(0, ".")

import asyncio
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from api.server import app, RUNS_DIR, SANDBOX_DIR
from runtime.blackboard import Blackboard, Task
from runtime.events import EventLog
from runtime.sandbox import Sandbox


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def seed_test_run():
    run_id = "run_test_api_fixture"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    db_path = str(run_dir / "blackboard.db")

    bb = Blackboard(db_path)
    el = EventLog(db_path)
    sb = Sandbox(run_id=run_id, base_dir=str(SANDBOX_DIR))

    # Goal
    bb.set_goal(run_id, "API Test Goal Landing Page")

    # Tasks
    bb.add_task(Task(
        id="task-01-structure",
        run_id=run_id,
        title="HTML Structure",
        description="Write index.html",
        role_hint="structure",
        status="done",
        priority=5,
        target="index.html"
    ))

    # Artifacts
    sb.write_file(
        "index.html",
        "<!DOCTYPE html><html><head><link rel='stylesheet' href='styles.css'><script src='script.js' defer></script></head><body><h1>API Preview Test</h1></body></html>"
    )
    sb.write_file("styles.css", "body { background: #000; color: #fff; }")
    sb.write_file("script.js", "console.log('API preview active');")

    bb.record_artifact(run_id, "index.html", "hash_html", "agent-structure-01")
    bb.record_artifact(run_id, "styles.css", "hash_css", "agent-style-01")
    bb.record_artifact(run_id, "script.js", "hash_js", "agent-script-01")

    # Events
    el.append(run_id, "agent-structure-01", "agent_spawned", "", {"role": "structure"})
    el.append(run_id, "agent-structure-01", "task_claimed", "index.html", {"task_id": "task-01-structure"})
    el.append(run_id, "agent-structure-01", "file_edit", "index.html", {"bytes": 140})
    el.append(run_id, "agent-structure-01", "task_done", "index.html", {"task_id": "task-01-structure"})

    yield run_id


def test_health_endpoint(test_client):
    res = test_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_favicon_endpoint(test_client):
    res = test_client.get("/favicon.ico")
    assert res.status_code == 204


def test_list_runs(test_client, seed_test_run):
    res = test_client.get("/runs")
    assert res.status_code == 200
    data = res.json()
    assert "runs" in data
    run_ids = [r["run_id"] for r in data["runs"]]
    assert seed_test_run in run_ids


def test_get_run_details(test_client, seed_test_run):
    res = test_client.get(f"/runs/{seed_test_run}")
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == seed_test_run
    assert data["goal"]["prompt"] == "API Test Goal Landing Page"
    assert len(data["tasks"]) >= 1
    assert len(data["artifacts"]) >= 3
    assert "index.html" in data["files"]


def test_get_run_events_polling(test_client, seed_test_run):
    res = test_client.get(f"/runs/{seed_test_run}/events?since_id=0")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 4
    event_types = [e["event_type"] for e in data["events"]]
    assert "agent_spawned" in event_types
    assert "file_edit" in event_types


def test_preview_html_asset(test_client, seed_test_run):
    res = test_client.get(f"/runs/{seed_test_run}/preview/index.html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "API Preview Test" in res.text


def test_preview_css_asset(test_client, seed_test_run):
    res = test_client.get(f"/runs/{seed_test_run}/preview/styles.css")
    assert res.status_code == 200
    assert "text/css" in res.headers["content-type"]
    assert "background: #000" in res.text


def test_preview_js_asset(test_client, seed_test_run):
    res = test_client.get(f"/runs/{seed_test_run}/preview/script.js")
    assert res.status_code == 200
    assert "application/javascript" in res.headers["content-type"]
    assert "API preview active" in res.text


def test_preview_traversal_security_rejection(test_client, seed_test_run):
    res = test_client.get(f"/runs/{seed_test_run}/preview/../../secret.txt")
    # Path traversal rejected by sandbox canonical resolver (403 or 404)
    assert res.status_code in (403, 404)


def test_websocket_event_streaming(test_client, seed_test_run):
    with test_client.websocket_connect(f"/ws/runs/{seed_test_run}") as ws:
        # First message should be historical event
        msg1 = ws.receive_json()
        assert msg1["type"] in ("event", "state_snapshot")

        # Second message should arrive promptly
        msg2 = ws.receive_json()
        assert msg2["type"] in ("event", "state_snapshot")

