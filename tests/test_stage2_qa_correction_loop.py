"""
Integration test for Stage 2 Automated QA and Correction Loop.
Verifies:
1. QA agent identifies defects and logs 'test_failed'.
2. QA creates high-priority fix task on blackboard and emits 'bug_found'.
3. Specialist agent claims fix task, writes repaired file, and logs 'fix_applied'.
4. QA agent re-verifies and logs 'test_run' pass.
"""

import sys
sys.path.insert(0, ".")

import pytest
from runtime.agent import SwarmAgent
from runtime.blackboard import Blackboard, Task
from runtime.events import EventLog
from runtime.llm import ActionPayload, QwenClient
from runtime.roles import ROLE_QA, ROLE_STRUCTURE
from runtime.sandbox import Sandbox


@pytest.mark.asyncio
async def test_qa_defect_detection_and_automated_correction(tmp_path):
    db_file = str(tmp_path / "blackboard.db")
    blackboard = Blackboard(db_file)
    event_log = EventLog(db_file)
    sandbox = Sandbox(run_id="run_qa_loop", base_dir=str(tmp_path / ".sandbox"))
    run_id = "run_qa_loop"

    blackboard.set_goal(run_id, "Build a portfolio with QA loop")

    # Write initial imperfect HTML (missing <!DOCTYPE html> and missing styles.css link)
    sandbox.write_file("index.html", "<html><body><h1>Imperfect Site</h1></body></html>")
    sandbox.write_file("styles.css", "body { color: white; }")
    sandbox.write_file("script.js", "console.log('ready');")

    mock_llm = QwenClient(model="mock_model")

    qa_agent = SwarmAgent(
        agent_id=ROLE_QA.default_agent_id,
        role=ROLE_QA.name,
        run_id=run_id,
        blackboard=blackboard,
        event_log=event_log,
        sandbox=sandbox,
        llm_client=mock_llm,
        system_prompt=ROLE_QA.system_prompt
    )

    structure_agent = SwarmAgent(
        agent_id=ROLE_STRUCTURE.default_agent_id,
        role=ROLE_STRUCTURE.name,
        run_id=run_id,
        blackboard=blackboard,
        event_log=event_log,
        sandbox=sandbox,
        llm_client=mock_llm,
        system_prompt=ROLE_STRUCTURE.system_prompt
    )

    # Add a QA task
    blackboard.add_task(Task(
        id="task-qa-01",
        run_id=run_id,
        title="Initial QA Audit",
        description="Run automated verification",
        role_hint="qa",
        priority=1,
        target="all"
    ))

    # 1. QA Agent steps: audits sandbox, fails, logs test_failed, and spawns fix tasks
    qa_acted = await qa_agent.step()
    assert qa_acted is True

    # Verify test_failed event logged
    events = event_log.get_events(run_id)
    event_types = [e.event_type for e in events]
    assert "test_failed" in event_types

    # Verify fix task was added to blackboard with priority 10
    tasks = blackboard.list_tasks(run_id)
    fix_tasks = [t for t in tasks if t.id.startswith("fix-")]
    assert len(fix_tasks) >= 1
    assert fix_tasks[0].priority == 10
    assert fix_tasks[0].role_hint == "structure"

    # Verify bug_found signal emitted
    signals = blackboard.get_active_signals(run_id)
    assert any(s.type == "bug_found" for s in signals)

    # 2. Structure Agent steps: claims fix task and writes repaired HTML
    repaired_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Repaired Site</title>
  <link rel="stylesheet" href="styles.css">
  <script src="script.js" defer></script>
</head>
<body>
  <h1>Repaired Site</h1>
</body>
</html>"""

    async def fake_fix_action(*args, **kwargs):
        return ActionPayload(
            action="write_file",
            task_id=fix_tasks[0].id,
            target="index.html",
            args={"path": "index.html", "content": repaired_html},
            reasoning_summary="Fixed missing DOCTYPE and added styles.css link"
        )

    mock_llm.generate_structured = fake_fix_action

    structure_acted = await structure_agent.step()
    assert structure_acted is True

    # Verify fix_applied event logged
    events_after_fix = event_log.get_events(run_id)
    fix_events = [e for e in events_after_fix if e.event_type == "fix_applied"]
    assert len(fix_events) >= 1
    assert fix_events[0].target == "index.html"

    # 3. QA Agent steps again: audits repaired project and passes
    qa_second_step = await qa_agent.step()
    assert qa_second_step is True

    # Verify test_run passed event logged
    final_events = event_log.get_events(run_id)
    pass_events = [e for e in final_events if e.event_type == "test_run" and e.payload.get("status") == "pass"]
    assert len(pass_events) == 1

    # Verify qa_passed signal emitted
    final_signals = blackboard.get_active_signals(run_id)
    assert any(s.type == "qa_passed" for s in final_signals)

