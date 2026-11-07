"""
End-to-end integration test for Stage 1.
Tests the agent observe-decide-act-report loop with SQLite blackboard and sandbox.
"""

import asyncio
import tempfile
import pathlib
import sys
import pytest

sys.path.insert(0, ".")

from runtime.blackboard import Blackboard
from runtime.events import EventLog
from runtime.sandbox import Sandbox
from runtime.agent import SwarmAgent
from runtime.llm import ActionPayload, InitialTasksPayload, QwenClient
from runtime.tools import verify_web_assets


@pytest.mark.asyncio
async def test_stage1_agent_loop_end_to_end(tmp_path):
    db_file = str(tmp_path / "blackboard.db")
    blackboard = Blackboard(db_file)
    event_log = EventLog(db_file)
    sandbox = Sandbox(run_id="test_run", base_dir=str(tmp_path / ".sandbox"))
    run_id = "test_run"

    blackboard.set_goal(run_id, "Build a simple personal portfolio")

    mock_llm = QwenClient(model="mock_model")

    mock_seeding_response = InitialTasksPayload(
        tasks=[
            {
                "id": "task-01",
                "title": "Create Landing Page",
                "description": "Write HTML structure with hero and about sections",
                "role_hint": "Frontend",
                "target": "index.html",
                "priority": 5
            }
        ]
    )

    mock_action_response = ActionPayload(
        action="write_file",
        task_id="task-01",
        target="index.html",
        args={
            "path": "index.html",
            "content": "<!DOCTYPE html><html><head><title>Alex Portfolio</title></head><body><h1>Hello World</h1></body></html>"
        },
        reasoning_summary="Wrote modern landing page HTML"
    )

    responses = [mock_seeding_response, mock_action_response]

    async def fake_generate(*args, **kwargs):
        if responses:
            return responses.pop(0)
        return ActionPayload(action="task_done", task_id="task-01")

    mock_llm.generate_structured = fake_generate

    agent = SwarmAgent(
        agent_id="agent-frontend-01",
        role="Frontend",
        run_id=run_id,
        blackboard=blackboard,
        event_log=event_log,
        sandbox=sandbox,
        llm_client=mock_llm
    )

    # Step 1: Seeds tasks and claims task-01, writes index.html, marks done
    has_more = await agent.step()
    assert has_more is True

    # Step 2: No more open tasks
    has_more_next = await agent.step()
    assert has_more_next is False

    # Assertions
    tasks = blackboard.list_tasks(run_id)
    assert len(tasks) == 1
    assert tasks[0].status == "done"
    assert tasks[0].owner == "agent-frontend-01"

    assert sandbox.file_exists("index.html") is True
    content = sandbox.read_file("index.html")
    assert "Alex Portfolio" in content

    verification = verify_web_assets(sandbox)
    assert verification["valid"] is True

    events = event_log.get_events(run_id)
    event_types = [e.event_type for e in events]
    assert "agent_spawned" in event_types
    assert "task_claimed" in event_types
    assert "file_edit" in event_types
    assert "task_done" in event_types
