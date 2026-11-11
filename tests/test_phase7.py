"""
Unit and Integration Tests for Phase 7 Dashboard Endpoints.
Verifies:
1. GET & PUT /runs/{run_id}/spec (Plan review & instant :root regeneration without LLM)
2. POST /runs/{run_id}/quick-edit (targeted task routing to specific file)
3. GET /runs/{run_id}/export/zip (downloadable ZIP bundle containing all sandbox files)
4. POST /runs/{run_id}/tasks/{task_id}/retry (task retry resets status)
5. GET /runs/{run_id}/versions (artifact version and modification history)
"""

import io
import json
import uuid
import zipfile
import pytest
from pathlib import Path
from api.server import (
    get_run_spec,
    update_run_spec,
    submit_quick_edit,
    export_sandbox_zip,
    retry_task,
    get_run_versions,
    UpdateSpecRequest,
    QuickEditRequest,
    RUNS_DIR,
    SANDBOX_DIR
)
from runtime.blackboard import Blackboard, Task
from runtime.events import EventLog
from runtime.sandbox import Sandbox
from runtime.spec import generate_default_spec


@pytest.fixture
def phase7_fixture(tmp_path):
    run_id = f"test_run_phase7_{uuid.uuid4().hex[:8]}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    db_path = str(run_dir / "blackboard.db")

    blackboard = Blackboard(db_path)
    event_log = EventLog(db_path)
    sandbox = Sandbox(run_id=run_id, base_dir=str(SANDBOX_DIR))

    # Seed SiteSpec
    spec = generate_default_spec("Modern bistro in Paris")
    spec_json = spec.model_dump_json(indent=2)
    sandbox.write_file("spec.json", spec_json)
    blackboard.record_artifact(run_id, "spec.json", "hash_spec", "coordinator")

    # Seed HTML & CSS files
    sandbox.write_file("index.html", "<!DOCTYPE html><html><body><h1>Bistro</h1></body></html>")
    sandbox.write_file("styles.css", "body { background: var(--bg); }")
    sandbox.write_file("script.js", "console.log('init');")
    blackboard.record_artifact(run_id, "index.html", "hash_html", "structure")
    blackboard.record_artifact(run_id, "styles.css", "hash_css", "style")

    # Seed Task
    blackboard.add_task(Task(
        id="task-02-styling",
        run_id=run_id,
        title="Page Styles",
        description="Write styles",
        role_hint="style",
        status="failed",
        priority=4,
        target="styles.css"
    ))

    yield run_id, blackboard, sandbox


def test_get_and_update_run_spec_instant_root_regeneration(phase7_fixture):
    run_id, blackboard, sandbox = phase7_fixture

    # 1. GET /runs/{run_id}/spec
    spec_data = get_run_spec(run_id)
    assert spec_data["brand_name"] != ""
    assert "theme" in spec_data

    # 2. PUT /runs/{run_id}/spec (modifying theme colors)
    modified_spec = dict(spec_data)
    modified_spec["theme"]["primary"] = "#ff0077"
    modified_spec["theme"]["mood"] = "vibrant"

    res = update_run_spec(run_id, UpdateSpecRequest(spec=modified_spec))
    assert res["status"] == "success"

    # Verify spec.json updated in sandbox
    updated_spec_json = json.loads(sandbox.read_file("spec.json"))
    assert updated_spec_json["theme"]["primary"] == "#ff0077"

    # Verify base.css automatically regenerated with zero LLM call
    assert sandbox.file_exists("base.css")
    base_css = sandbox.read_file("base.css")
    assert "--primary: #ff0077;" in base_css


def test_submit_quick_edit_targeted_routing(phase7_fixture):
    run_id, blackboard, sandbox = phase7_fixture

    # Submit quick edit targeting styles.css
    req = QuickEditRequest(instruction="make the hero background darker", target_file="styles.css")
    res = submit_quick_edit(run_id, req)

    assert res["status"] == "queued"
    assert res["role"] == "style"
    assert res["target"] == "styles.css"

    # Verify task was added to blackboard with priority 9
    tasks = blackboard.list_tasks(run_id)
    quick_tasks = [t for t in tasks if t.id.startswith("quick-edit-")]
    assert len(quick_tasks) == 1
    assert quick_tasks[0].priority == 9
    assert "make the hero background darker" in quick_tasks[0].description


def test_export_sandbox_zip_archive(phase7_fixture):
    run_id, blackboard, sandbox = phase7_fixture

    response = export_sandbox_zip(run_id)
    assert response.status_code == 200
    assert response.media_type == "application/zip"
    assert "Content-Disposition" in response.headers

    # Validate ZIP integrity
    zip_buf = io.BytesIO(response.body)
    with zipfile.ZipFile(zip_buf, "r") as zf:
        namelist = zf.namelist()
        assert "index.html" in namelist
        assert "styles.css" in namelist
        assert "spec.json" in namelist
        # Verify uncompressed content matches sandbox
        assert zf.read("index.html").decode("utf-8") == sandbox.read_file("index.html")


def test_retry_task_status_reset(phase7_fixture):
    run_id, blackboard, sandbox = phase7_fixture

    task = blackboard.get_task(run_id, "task-02-styling")
    assert task.status == "failed"

    res = retry_task(run_id, "task-02-styling")
    assert res["status"] == "retried"

    updated_task = blackboard.get_task(run_id, "task-02-styling")
    assert updated_task.status == "open"


def test_get_run_versions(phase7_fixture):
    run_id, blackboard, sandbox = phase7_fixture

    versions = get_run_versions(run_id)
    assert "artifacts" in versions
    assert len(versions["artifacts"]) >= 3
    paths = [a["path"] for a in versions["artifacts"]]
    assert "index.html" in paths
    assert "styles.css" in paths
    assert "spec.json" in paths
