"""
FastAPI Server for Swarm Website Builder (Stage 3).
Provides REST endpoints and Starlette WebSocket streaming for real-time swarm observation:
- POST /runs : Start new autonomous swarm generation
- GET /runs : List all runs
- GET /runs/{run_id} : Get status, blackboard tasks, artifacts, and QA score
- GET /runs/{run_id}/events : Polling query for events since_id
- GET /runs/{run_id}/preview/{path:path} : Live sandbox web asset preview
- WS /ws/runs/{run_id} : Real-time WebSocket streaming events and blackboard states
"""

import asyncio
import io
import json
import logging
import mimetypes
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import zipfile

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from runtime.blackboard import Blackboard
from runtime.events import EventLog
from runtime.llm import QwenClient
from runtime.qa import run_qa_audit
from runtime.sandbox import Sandbox, SandboxSecurityViolation
from runtime.swarm import Swarm
from runtime.vision.feedback import VisionFeedbackLoop

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "runs"
SANDBOX_DIR = REPO_ROOT / ".sandbox"

RUNS_DIR.mkdir(parents=True, exist_ok=True)
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("api.server")

app = FastAPI(
    title="Swarm Website Builder API",
    description="Decentralized Multi-Agent Swarm with Real-Time Event Streaming",
    version="1.0.0"
)

# Enable CORS for local Vite and React development (Stage 4)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active in-memory swarm tasks: run_id -> asyncio.Task
ACTIVE_RUNS: Dict[str, asyncio.Task] = {}
RUN_STATUSES: Dict[str, str] = {}  # run_id -> "running" | "converged" | "failed"


class RunRequest(BaseModel):
    prompt: str = Field(description="Goal prompt for the website")
    reference_image: Optional[str] = Field(default=None, description="Optional path to reference image")
    model: Optional[str] = Field(default="qwen3.5:4b", description="Model name in Ollama")


def get_run_components(run_id: str):
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    db_path = str(run_dir / "blackboard.db")

    blackboard = Blackboard(db_path)
    event_log = EventLog(db_path)
    sandbox = Sandbox(run_id=run_id, base_dir=str(SANDBOX_DIR))
    return blackboard, event_log, sandbox


async def execute_swarm_task(run_id: str, prompt: str, model: str, reference_image: Optional[str] = None):
    """Background coroutine that executes the decentralized swarm until convergence."""
    logger.info(f"Background swarm execution started for run '{run_id}'")
    RUN_STATUSES[run_id] = "running"
    try:
        blackboard, event_log, sandbox = get_run_components(run_id)
        llm_client = QwenClient(model=model)
        vision_loop = VisionFeedbackLoop(runs_dir=RUNS_DIR)

        swarm = Swarm(
            run_id=run_id,
            goal_prompt=prompt,
            blackboard=blackboard,
            event_log=event_log,
            sandbox=sandbox,
            llm_client=llm_client,
            reference_image=reference_image,
            vision_loop=vision_loop
        )

        res = await swarm.run(max_seconds=1200.0)
        RUN_STATUSES[run_id] = "converged" if res.get("converged") else "failed"

        # Export events to events.jsonl
        jsonl_path = RUNS_DIR / run_id / "events.jsonl"
        event_log.export_jsonl(run_id, str(jsonl_path))
        logger.info(f"Swarm '{run_id}' finished with status '{RUN_STATUSES[run_id]}'")

    except asyncio.CancelledError:
        logger.warning(f"Swarm task '{run_id}' was cancelled.")
        RUN_STATUSES[run_id] = "cancelled"
    except Exception as e:
        logger.error(f"Error in swarm background execution '{run_id}': {e}", exc_info=True)
        RUN_STATUSES[run_id] = "failed"
    finally:
        ACTIVE_RUNS.pop(run_id, None)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Silence browser favicon requests with 204 No Content."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "swarm-website-builder-api",
        "active_swarms": len(ACTIVE_RUNS),
        "timestamp": time.time()
    }


@app.post("/runs", status_code=status.HTTP_201_CREATED)
async def start_run(req: RunRequest):
    """Spawn a new autonomous decentralized swarm run."""
    run_id = f"run_{int(time.time())}"
    blackboard, _, _ = get_run_components(run_id)
    blackboard.set_goal(run_id, req.prompt, req.reference_image)

    task = asyncio.create_task(execute_swarm_task(run_id, req.prompt, req.model or "qwen3.5:4b", req.reference_image))
    ACTIVE_RUNS[run_id] = task
    RUN_STATUSES[run_id] = "running"

    return {
        "run_id": run_id,
        "status": "running",
        "prompt": req.prompt,
        "model": req.model,
        "preview_url": f"/runs/{run_id}/preview/index.html",
        "websocket_url": f"/ws/runs/{run_id}"
    }


@app.get("/runs")
def list_runs():
    """List all past and active runs."""
    runs = []
    if RUNS_DIR.exists():
        for d in sorted(RUNS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if d.is_dir() and d.name.startswith("run_"):
                run_id = d.name
                db_path = d / "blackboard.db"
                prompt = ""
                created_at = d.stat().st_mtime
                run_status = RUN_STATUSES.get(run_id)
                if db_path.exists():
                    bb = Blackboard(str(db_path))
                    goal = bb.get_goal(run_id)
                    if goal:
                        prompt = goal.get("prompt", "")
                        created_at = goal.get("created_at", created_at)
                    if not run_status:
                        run_status = "converged" if bb.is_swarm_converged(run_id) else "incomplete"

                runs.append({
                    "run_id": run_id,
                    "status": run_status or "incomplete",
                    "prompt": prompt,
                    "created_at": created_at,
                    "is_active": run_id in ACTIVE_RUNS
                })
    return {"runs": runs}


@app.get("/runs/{run_id}")
def get_run_details(run_id: str):
    """Retrieve full run details: goal, blackboard tasks, artifacts, signals, and QA audit."""
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    blackboard, event_log, sandbox = get_run_components(run_id)

    goal = blackboard.get_goal(run_id) or {}
    tasks = blackboard.list_tasks(run_id)
    artifacts = blackboard.list_artifacts(run_id)
    signals = blackboard.get_active_signals(run_id)
    qa_report = run_qa_audit(sandbox)

    spec_data = None
    if sandbox.file_exists("spec.json"):
        try:
            spec_data = json.loads(sandbox.read_file("spec.json"))
        except Exception:
            pass

    return {
        "run_id": run_id,
        "status": RUN_STATUSES.get(run_id, "completed"),
        "is_active": run_id in ACTIVE_RUNS,
        "goal": goal,
        "spec": spec_data,
        "tasks": [t.model_dump() for t in tasks],
        "artifacts": [a.model_dump() for a in artifacts],
        "signals": [s.model_dump() for s in signals],
        "qa": {
            "passed": qa_report.passed,
            "score": qa_report.score,
            "defects": [d.__dict__ for d in qa_report.defects],
            "checks_passed": qa_report.checks_passed
        },
        "vision": [f.name for f in (run_dir / "vision").glob("*.png")] if (run_dir / "vision").exists() else [],
        "files": sandbox.list_files()
    }


@app.get("/runs/{run_id}/vision/{filename}")
def get_vision_asset(run_id: str, filename: str):
    """Serve vision iteration screenshots and visual diff comparison maps."""
    vision_file = RUNS_DIR / run_id / "vision" / filename
    if not vision_file.exists():
        raise HTTPException(status_code=404, detail="Vision asset not found")
    return FileResponse(str(vision_file), media_type="image/png")


@app.get("/runs/{run_id}/events")
def get_run_events(run_id: str, since_id: int = 0):
    """Query append-only event log incrementally."""
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    _, event_log, _ = get_run_components(run_id)
    events = event_log.get_events(run_id, since_id=since_id)

    return {
        "run_id": run_id,
        "since_id": since_id,
        "count": len(events),
        "events": [e.model_dump() for e in events]
    }


@app.get("/runs/{run_id}/preview/{path:path}")
def preview_sandbox_file(run_id: str, path: str = ""):
    """
    Serve live sandboxed website assets (index.html, styles.css, script.js, etc.).
    Guarantees path containment within .sandbox/<run_id>/ via Sandbox resolution.
    """
    if not path or path == "/":
        path = "index.html"

    sandbox = Sandbox(run_id=run_id, base_dir=str(SANDBOX_DIR))

    try:
        resolved_path = sandbox.resolve_path(path)
    except SandboxSecurityViolation as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{path}' not found in sandbox for run '{run_id}'"
        )

    mime_type, _ = mimetypes.guess_type(str(resolved_path))
    if path.endswith(".css"):
        mime_type = "text/css"
    elif path.endswith(".js"):
        mime_type = "application/javascript"
    elif path.endswith(".html"):
        mime_type = "text/html; charset=utf-8"

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
    }
    return FileResponse(resolved_path, media_type=mime_type or "text/plain", headers=headers)


class UpdateSpecRequest(BaseModel):
    spec: Dict[str, Any]


class QuickEditRequest(BaseModel):
    instruction: str
    target_file: Optional[str] = "styles.css"


@app.get("/runs/{run_id}/spec")
def get_run_spec(run_id: str):
    """Retrieve the SiteSpec contract (spec.json) if available."""
    sandbox = Sandbox(run_id=run_id, base_dir=str(SANDBOX_DIR))
    if not sandbox.file_exists("spec.json"):
        raise HTTPException(status_code=404, detail="spec.json not yet synthesized for this run")
    try:
        spec_content = sandbox.read_file("spec.json")
        return json.loads(spec_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read spec.json: {e}")


@app.put("/runs/{run_id}/spec")
def update_run_spec(run_id: str, req: UpdateSpecRequest):
    """
    Update the SiteSpec contract and instantly regenerate base.css (:root variables and components)
    with zero LLM call.
    """
    from runtime.spec import SiteSpec
    from runtime.theme import generate_base_css

    sandbox = Sandbox(run_id=run_id, base_dir=str(SANDBOX_DIR))
    blackboard, event_log, _ = get_run_components(run_id)

    try:
        spec_obj = SiteSpec(**req.spec)
        spec_json = spec_obj.model_dump_json(indent=2)
        write_res = sandbox.write_file("spec.json", spec_json)
        blackboard.record_artifact(run_id, "spec.json", write_res, "user-plan-review")

        # Deterministically update base.css with zero LLM call
        base_css_content = generate_base_css(spec_obj.theme)
        base_res = sandbox.write_file("base.css", base_css_content)
        blackboard.record_artifact(run_id, "base.css", base_res, "user-plan-review")

        event_log.append(
            run_id=run_id,
            agent_id="user",
            event_type="file_edit",
            target="spec.json",
            payload={"summary": "Updated SiteSpec theme and plan via Plan Review screen"}
        )

        return {"status": "success", "message": "SiteSpec and base.css updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid spec data: {e}")


@app.post("/runs/{run_id}/quick-edit")
def submit_quick_edit(run_id: str, req: QuickEditRequest):
    """
    Route a micro-instruction (e.g. 'make the hero darker') as a single targeted task to one file
    without a full site rebuild.
    """
    from runtime.blackboard import Task

    blackboard, event_log, sandbox = get_run_components(run_id)

    target_file = req.target_file or "styles.css"
    role_hint = "style" if target_file.endswith(".css") else "script" if target_file.endswith(".js") else "structure"

    task_id = f"quick-edit-{target_file.replace('.', '-')}-{int(time.time() * 1000) % 10000}"
    new_task = Task(
        id=task_id,
        run_id=run_id,
        title=f"Quick Edit ({target_file}): {req.instruction[:50]}",
        description=f"User requested targeted quick edit on {target_file}: '{req.instruction}'. Apply this edit concisely.",
        role_hint=role_hint,
        status="open",
        priority=9,
        target=target_file
    )
    blackboard.add_task(new_task)
    blackboard.emit_signal(run_id, f"need_{role_hint}", target_file, "user", initial_strength=2.0)

    event_log.append(
        run_id=run_id,
        agent_id="user",
        event_type="quick_edit_submitted",
        target=target_file,
        payload={"task_id": task_id, "instruction": req.instruction}
    )

    return {"status": "queued", "task_id": task_id, "role": role_hint, "target": target_file}


@app.get("/runs/{run_id}/export/zip")
def export_sandbox_zip(run_id: str):
    """Package the generated website files into a downloadable ZIP archive."""
    sandbox = Sandbox(run_id=run_id, base_dir=str(SANDBOX_DIR))
    files = sandbox.list_files()
    if not files:
        raise HTTPException(status_code=404, detail="No files found in sandbox to export")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for f in files:
            if f.startswith("."):
                continue
            content = sandbox.read_file(f)
            zip_file.writestr(f, content)

    buf.seek(0)
    headers = {
        "Content-Disposition": f'attachment; filename="{run_id}_website.zip"'
    }
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers=headers
    )


@app.post("/runs/{run_id}/tasks/{task_id}/retry")
def retry_task(run_id: str, task_id: str):
    """Reset a task to 'open' state to allow swarm agents to re-execute it."""
    blackboard, event_log, _ = get_run_components(run_id)
    task = blackboard.get_task(run_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    blackboard.update_task_status(run_id, task_id, None, "open")
    if task.target:
        blackboard.emit_signal(run_id, f"need_{task.role_hint}", task.target, "user-retry", initial_strength=1.5)

    event_log.append(
        run_id=run_id,
        agent_id="user",
        event_type="task_retried",
        target=task.target or "",
        payload={"task_id": task_id}
    )

    return {"status": "retried", "task_id": task_id}


@app.get("/runs/{run_id}/versions")
def get_run_versions(run_id: str):
    """List artifact modification history and versions for the run."""
    blackboard, event_log, sandbox = get_run_components(run_id)
    artifacts = blackboard.list_artifacts(run_id)
    events = event_log.get_events(run_id, since_id=0)
    file_events = [e for e in events if e.event_type in ("file_edit", "fix_applied")]

    return {
        "artifacts": [a.model_dump() for a in artifacts],
        "history": [e.model_dump() for e in file_events]
    }


@app.websocket("/ws/runs/{run_id}")
async def websocket_event_stream(websocket: WebSocket, run_id: str):
    """
    Real-time Starlette WebSocket streaming:
    Pushes incremental events and periodic blackboard state snapshots.
    """
    await websocket.accept()
    logger.info(f"WebSocket client connected for run '{run_id}'")

    blackboard, event_log, sandbox = get_run_components(run_id)
    last_event_id = 0

    try:
        # Stream all initial historical events without triggering hot reload storm
        initial_events = event_log.get_events(run_id, since_id=0)
        for ev in initial_events:
            await websocket.send_json({"type": "history_event", "data": ev.model_dump()})
            if ev.id and ev.id > last_event_id:
                last_event_id = ev.id

        # Periodic streaming loop
        tick = 0
        while True:
            # 1. Check for new events
            new_events = event_log.get_events(run_id, since_id=last_event_id)
            for ev in new_events:
                await websocket.send_json({"type": "event", "data": ev.model_dump()})
                if ev.id and ev.id > last_event_id:
                    last_event_id = ev.id

            # 2. Every 2 seconds (10 ticks * 200ms), push a state snapshot
            if tick % 10 == 0:
                tasks = blackboard.list_tasks(run_id)
                signals = blackboard.get_active_signals(run_id)
                artifacts = blackboard.list_artifacts(run_id)
                files = sandbox.list_files()
                await websocket.send_json({
                    "type": "state_snapshot",
                    "data": {
                        "status": RUN_STATUSES.get(run_id, "converged" if blackboard.is_swarm_converged(run_id) else "running"),
                        "tasks": [t.model_dump() for t in tasks],
                        "signals": [s.model_dump() for s in signals],
                        "artifacts": [a.model_dump() for a in artifacts],
                        "files": files,
                    }
                })

            tick += 1
            await asyncio.sleep(0.2)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for run '{run_id}'")
    except Exception as e:
        logger.error(f"WebSocket error in stream for '{run_id}': {e}")


# Serve compiled React + Vite dashboard at root if built (Stage 4)
UI_DIST_DIR = REPO_ROOT / "ui" / "dist"
if UI_DIST_DIR.exists():
    from starlette.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(UI_DIST_DIR), html=True), name="ui")

