"""
Event Log - Single Source of Truth for Swarm Website Builder.
Every action in the multi-agent system is recorded in an append-only log.
The UI and cursors only replay real logged events.
"""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

VALID_EVENT_TYPES = {
    "agent_spawned",
    "task_claimed",
    "file_edit",
    "signal_emitted",
    "test_run",
    "test_failed",
    "fix_applied",
    "agent_failed",
    "agent_recovered",
    "task_done"
}


class Event(BaseModel):
    id: Optional[int] = None
    ts: float = Field(default_factory=time.time)
    run_id: str
    agent_id: str
    event_type: str
    target: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class EventLog:
    """Append-only event logger backed by SQLite."""

    def __init__(self, db_path: str = "swarm.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    run_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_run_id ON events (run_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts);")
            conn.commit()

    def append(self, run_id: str, agent_id: str, event_type: str, target: str, payload: Optional[Dict[str, Any]] = None) -> Event:
        if event_type not in VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event_type '{event_type}'. Must be one of {VALID_EVENT_TYPES}")

        payload_dict = payload or {}
        payload_str = json.dumps(payload_dict)
        now = time.time()

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO events (ts, run_id, agent_id, event_type, target, payload)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (now, run_id, agent_id, event_type, target, payload_str))
            conn.commit()
            event_id = cur.lastrowid

        return Event(
            id=event_id,
            ts=now,
            run_id=run_id,
            agent_id=agent_id,
            event_type=event_type,
            target=target,
            payload=payload_dict
        )

    def get_events(self, run_id: str, since_id: int = 0) -> List[Event]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, ts, run_id, agent_id, event_type, target, payload
                FROM events
                WHERE run_id = ? AND id > ?
                ORDER BY id ASC
            """, (run_id, since_id))
            rows = cur.fetchall()

        events = []
        for r in rows:
            events.append(Event(
                id=r["id"],
                ts=r["ts"],
                run_id=r["run_id"],
                agent_id=r["agent_id"],
                event_type=r["event_type"],
                target=r["target"],
                payload=json.loads(r["payload"])
            ))
        return events

    def export_jsonl(self, run_id: str, file_path: str) -> int:
        events = self.get_events(run_id)
        out_path = Path(file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for ev in events:
                f.write(ev.model_dump_json() + "\n")
        return len(events)
