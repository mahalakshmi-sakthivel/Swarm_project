"""
Unit tests for Append-Only Event Log:
- Event appending and structure
- Event schema validation
- Extraction by since_id
- JSONL export verification
"""

import json
import pytest
from runtime.events import EventLog, VALID_EVENT_TYPES


@pytest.fixture
def event_log(tmp_path):
    db_file = tmp_path / "test_events.db"
    return EventLog(str(db_file))


def test_append_and_retrieve_events(event_log):
    run_id = "run-ev-01"
    ev1 = event_log.append(run_id, "agent-ui", "agent_spawned", "", {"role": "UI/UX"})
    assert ev1.id == 1
    assert ev1.event_type == "agent_spawned"

    ev2 = event_log.append(run_id, "agent-fe", "file_edit", "index.html", {"bytes": 450})
    assert ev2.id == 2
    assert ev2.event_type == "file_edit"

    events = event_log.get_events(run_id)
    assert len(events) == 2
    assert events[0].agent_id == "agent-ui"
    assert events[1].target == "index.html"


def test_reject_invalid_event_type(event_log):
    run_id = "run-ev-02"
    with pytest.raises(ValueError, match="Invalid event_type"):
        event_log.append(run_id, "agent-1", "fake_fabricated_event", "")


def test_incremental_streaming_since_id(event_log):
    run_id = "run-ev-03"
    for i in range(5):
        event_log.append(run_id, f"agent-{i}", "signal_emitted", "hero", {"idx": i})

    all_evs = event_log.get_events(run_id)
    assert len(all_evs) == 5

    streamed = event_log.get_events(run_id, since_id=3)
    assert len(streamed) == 2
    assert streamed[0].id == 4
    assert streamed[1].id == 5


def test_export_jsonl(event_log, tmp_path):
    run_id = "run-ev-04"
    event_log.append(run_id, "agent-1", "task_claimed", "index.html", {"task": "t1"})
    event_log.append(run_id, "agent-1", "task_done", "index.html", {"task": "t1"})

    export_file = tmp_path / "events.jsonl"
    count = event_log.export_jsonl(run_id, str(export_file))
    assert count == 2
    assert export_file.exists()

    lines = export_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    parsed_first = json.loads(lines[0])
    assert parsed_first["event_type"] == "task_claimed"

