"""
Integration Tests for Stage 5 Vision Feedback Loop (VisionFeedbackLoop).
Tests:
- Iteration execution on sandbox with matching reference (convergence)
- Iteration execution on sandbox with mismatching reference:
  - Emits visual_mismatch signal
  - Creates targeted style and structure repair tasks with priority 10
  - Appends qa_audit event to event log with vision payload
"""

import sys
sys.path.insert(0, ".")

from pathlib import Path
from PIL import Image, ImageDraw
import pytest

from runtime.blackboard import Blackboard
from runtime.events import EventLog
from runtime.sandbox import Sandbox
from runtime.vision.feedback import VisionFeedbackLoop


@pytest.fixture
def vision_env(tmp_path):
    run_id = "run_vision_test"
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    db_path = str(runs_dir / "test_blackboard.db")

    bb = Blackboard(db_path)
    el = EventLog(db_path)
    sb = Sandbox(run_id=run_id, base_dir=str(tmp_path / ".sandbox"))

    # Seed sandbox HTML and CSS
    sb.write_file(
        "index.html",
        "<!DOCTYPE html><html><head><link rel='stylesheet' href='styles.css'></head><body><h1>Vision Test</h1></body></html>"
    )
    sb.write_file("styles.css", "body { background: #000; color: #fff; }")

    # Generate synthetic reference image
    ref_path = tmp_path / "mockup_reference.png"
    img = Image.new("RGB", (1280, 800), color="#ffffff")
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (1280, 80)], fill="#ff0000")
    img.save(str(ref_path), "PNG")

    loop = VisionFeedbackLoop(runs_dir=runs_dir, convergence_threshold=0.85, max_iterations=3)

    return {
        "run_id": run_id,
        "runs_dir": runs_dir,
        "blackboard": bb,
        "event_log": el,
        "sandbox": sb,
        "reference_image": ref_path,
        "loop": loop,
    }


def test_vision_loop_mismatch_creates_repair_tasks(vision_env):
    """When generated screenshot differs from reference, loop generates repair tasks."""
    bb = vision_env["blackboard"]
    el = vision_env["event_log"]
    sb = vision_env["sandbox"]
    loop = vision_env["loop"]
    run_id = vision_env["run_id"]
    ref_img = vision_env["reference_image"]

    result = loop.run_iteration(
        run_id=run_id,
        blackboard=bb,
        event_log=el,
        sandbox=sb,
        reference_image_path=ref_img,
        iteration=1,
    )

    # Result should be unconverged (black page vs white/red reference mockup)
    assert result.converged is False
    assert result.composite_score < 0.85

    # Verify signals emitted
    signals = bb.get_active_signals(run_id)
    signal_types = [s.type for s in signals]
    assert "visual_mismatch" in signal_types

    # Verify repair tasks created
    tasks = bb.list_tasks(run_id)
    assert len(tasks) >= 1
    style_task = next((t for t in tasks if t.role_hint == "style"), None)
    assert style_task is not None
    assert style_task.priority == 10
    assert "Visual Alignment" in style_task.title

    # Verify event logged
    events = el.get_events(run_id)
    audit_event = next((e for e in events if e.event_type == "test_run" and e.target == "vision"), None)
    assert audit_event is not None
    assert audit_event.payload["iteration"] == 1
    assert "composite_score" in audit_event.payload


def test_vision_loop_convergence_on_matching_reference(vision_env, tmp_path):
    """When reference matches the screenshot, loop converges and emits pass signal."""
    bb = vision_env["blackboard"]
    el = vision_env["event_log"]
    sb = vision_env["sandbox"]
    loop = vision_env["loop"]
    run_id = "run_vision_match"

    # Pre-capture current sandbox screenshot to use as identical reference
    capturer = loop.capturer
    matching_ref = tmp_path / "exact_match_ref.png"
    capturer.capture(sb.sandbox_dir / "index.html", matching_ref)

    result = loop.run_iteration(
        run_id=run_id,
        blackboard=bb,
        event_log=el,
        sandbox=sb,
        reference_image_path=matching_ref,
        iteration=1,
    )

    assert result.converged is True
    assert result.composite_score >= 0.85

    # Verify pass signal
    signals = bb.get_active_signals(run_id)
    pass_signal = next((s for s in signals if s.type == "visual_alignment_passed"), None)
    assert pass_signal is not None
