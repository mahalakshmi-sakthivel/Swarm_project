"""
Blackboard - Shared Memory & Stigmergic Coordination Mechanism.
Implements Non-Negotiable Rules:
- No central controller (coordination through shared state)
- Atomic claims and leases with automatic expiry back to 'open'
- Optimistic versioning on artifacts
- Signals with decay and reinforcement
"""

from contextlib import contextmanager
import json
import math
import sqlite3
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Task(BaseModel):
    id: str
    run_id: str
    title: str
    description: str
    role_hint: str
    status: str = "open"  # open | claimed | in_progress | in_review | done | failed
    owner: Optional[str] = None
    lease_expires_at: Optional[float] = None
    depends_on: List[str] = Field(default_factory=list)
    priority: int = 1
    target: str = ""
    created_at: float = Field(default_factory=time.time)
    version: int = 1


class Artifact(BaseModel):
    id: str
    run_id: str
    path: str
    content_hash: str
    version: int = 1
    author_agent: str
    created_at: float = Field(default_factory=time.time)


class Signal(BaseModel):
    id: Optional[int] = None
    run_id: str
    type: str  # need_styling | bug_found | needs_review | blocked | ...
    target: str
    strength: float = 1.0
    emitter_agent: str
    created_at: float = Field(default_factory=time.time)
    last_reinforced_at: float = Field(default_factory=time.time)


class Blackboard:
    """SQLite-backed blackboard with atomic operations and transactional safety."""

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
            
            # Goals
            conn.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    run_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    reference_image TEXT,
                    created_at REAL NOT NULL
                );
            """)

            # Tasks
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    role_hint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    owner TEXT,
                    lease_expires_at REAL,
                    depends_on TEXT NOT NULL, -- JSON list
                    priority INTEGER NOT NULL DEFAULT 1,
                    target TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (run_id, id)
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (run_id, status);")

            # Artifacts
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    author_agent TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (run_id, path)
                );
            """)

            # Signals
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    strength REAL NOT NULL,
                    emitter_agent TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_reinforced_at REAL NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_type ON signals (run_id, type, target);")

            # Scores
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    score_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    iteration INTEGER NOT NULL,
                    created_at REAL NOT NULL
                );
            """)
            conn.commit()

    # --- GOAL ZONE ---
    def set_goal(self, run_id: str, prompt: str, reference_image: Optional[str] = None):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO goals (run_id, prompt, reference_image, created_at)
                VALUES (?, ?, ?, ?)
            """, (run_id, prompt, reference_image, time.time()))
            conn.commit()

    def get_goal(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT run_id, prompt, reference_image, created_at FROM goals WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
        return None

    # --- TASK ZONE ---
    def add_task(self, task: Task) -> bool:
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tasks (
                    id, run_id, title, description, role_hint, status, owner,
                    lease_expires_at, depends_on, priority, target, created_at, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id, task.run_id, task.title, task.description, task.role_hint,
                task.status, task.owner, task.lease_expires_at, json.dumps(task.depends_on),
                task.priority, task.target, task.created_at, task.version
            ))
            conn.commit()
            return True

    def get_task(self, run_id: str, task_id: str) -> Optional[Task]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM tasks WHERE run_id = ? AND id = ?", (run_id, task_id))
            row = cur.fetchone()
            if row:
                return Task(
                    id=row["id"],
                    run_id=row["run_id"],
                    title=row["title"],
                    description=row["description"],
                    role_hint=row["role_hint"],
                    status=row["status"],
                    owner=row["owner"],
                    lease_expires_at=row["lease_expires_at"],
                    depends_on=json.loads(row["depends_on"]),
                    priority=row["priority"],
                    target=row["target"],
                    created_at=row["created_at"],
                    version=row["version"],
                )
        return None

    def list_tasks(self, run_id: str, status: Optional[str] = None, role_hint: Optional[str] = None) -> List[Task]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM tasks WHERE run_id = ?"
            params: List[Any] = [run_id]

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY priority DESC, created_at ASC"
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

        all_tasks = [
            Task(
                id=r["id"],
                run_id=r["run_id"],
                title=r["title"],
                description=r["description"],
                role_hint=r["role_hint"],
                status=r["status"],
                owner=r["owner"],
                lease_expires_at=r["lease_expires_at"],
                depends_on=json.loads(r["depends_on"]),
                priority=r["priority"],
                target=r["target"],
                created_at=r["created_at"],
                version=r["version"],
            ) for r in rows
        ]

        if not role_hint or role_hint == "any":
            return all_tasks

        # Import role matching
        from runtime.roles import get_role_by_hint
        agent_role = get_role_by_hint(role_hint)

        matching_tasks = []
        for t in all_tasks:
            if t.role_hint.lower() in (role_hint.lower(), "any"):
                matching_tasks.append(t)
            elif agent_role and get_role_by_hint(t.role_hint) == agent_role:
                matching_tasks.append(t)

        return matching_tasks

    def claim_task_atomic(self, run_id: str, task_id: str, agent_id: str, lease_duration_sec: float = 60.0) -> bool:
        """
        Atomic claim using single UPDATE with compare-and-set.
        Succeeds only if task is currently 'open' OR lease has expired.
        """
        now = time.time()
        expires_at = now + lease_duration_sec

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE tasks
                SET status = 'claimed',
                    owner = ?,
                    lease_expires_at = ?,
                    version = version + 1
                WHERE run_id = ?
                  AND id = ?
                  AND (status = 'open' OR (status IN ('claimed', 'in_progress') AND lease_expires_at < ?))
            """, (agent_id, expires_at, run_id, task_id, now))
            conn.commit()
            return cur.rowcount == 1

    def update_task_status(self, run_id: str, task_id: str, agent_id: Optional[str], new_status: str) -> bool:
        """Update task status (e.g. in_progress, done, failed). If resetting to 'open', clears owner and lease."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            if new_status == "open":
                cur.execute("""
                    UPDATE tasks
                    SET status = 'open',
                        owner = NULL,
                        lease_expires_at = NULL,
                        version = version + 1
                    WHERE run_id = ? AND id = ?
                """, (run_id, task_id))
            else:
                cur.execute("""
                    UPDATE tasks
                    SET status = ?,
                        version = version + 1
                    WHERE run_id = ? AND id = ? AND owner = ?
                """, (new_status, run_id, task_id, agent_id))
            conn.commit()
            return cur.rowcount == 1

    def reopen_expired_leases(self, run_id: str) -> int:
        """Check all tasks with expired leases and return them to 'open' status."""
        now = time.time()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE tasks
                SET status = 'open',
                    owner = NULL,
                    lease_expires_at = NULL,
                    version = version + 1
                WHERE run_id = ?
                  AND status IN ('claimed', 'in_progress')
                  AND lease_expires_at < ?
            """, (run_id, now))
            conn.commit()
            return cur.rowcount

    # --- ARTIFACT ZONE ---
    def record_artifact(self, run_id: str, path: str, content_hash: str, author_agent: str, expected_version: Optional[int] = None) -> Artifact:
        """
        Optimistic concurrency control for artifacts.
        If expected_version is provided, fails if artifact version != expected_version.
        """
        now = time.time()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT version FROM artifacts WHERE run_id = ? AND path = ?", (run_id, path))
            row = cur.fetchone()

            if row:
                current_ver = row["version"]
                if expected_version is not None and current_ver != expected_version:
                    raise ValueError(f"Optimistic lock conflict on artifact '{path}': expected v{expected_version}, found v{current_ver}")
                new_ver = current_ver + 1
                cur.execute("""
                    UPDATE artifacts
                    SET content_hash = ?, version = ?, author_agent = ?, created_at = ?
                    WHERE run_id = ? AND path = ?
                """, (content_hash, new_ver, author_agent, now, run_id, path))
            else:
                new_ver = 1
                cur.execute("""
                    INSERT INTO artifacts (id, run_id, path, content_hash, version, author_agent, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (f"art-{int(now*1000)}", run_id, path, content_hash, new_ver, author_agent, now))

            conn.commit()
            return Artifact(
                id=f"art-{path}",
                run_id=run_id,
                path=path,
                content_hash=content_hash,
                version=new_ver,
                author_agent=author_agent,
                created_at=now
            )

    def get_artifact(self, run_id: str, path: str) -> Optional[Artifact]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM artifacts WHERE run_id = ? AND path = ?", (run_id, path))
            row = cur.fetchone()
            if row:
                return Artifact(
                    id=row["id"],
                    run_id=row["run_id"],
                    path=row["path"],
                    content_hash=row["content_hash"],
                    version=row["version"],
                    author_agent=row["author_agent"],
                    created_at=row["created_at"],
                )
        return None

    # --- SIGNAL ZONE (Pheromones) ---
    def emit_signal(self, run_id: str, sig_type: str, target: str, emitter: str, initial_strength: float = 1.0) -> Signal:
        """Emit or reinforce a signal on target."""
        now = time.time()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, strength FROM signals
                WHERE run_id = ? AND type = ? AND target = ?
            """, (run_id, sig_type, target))
            row = cur.fetchone()

            if row:
                # Reinforce
                new_strength = row["strength"] + initial_strength
                cur.execute("""
                    UPDATE signals
                    SET strength = ?, last_reinforced_at = ?
                    WHERE id = ?
                """, (new_strength, now, row["id"]))
                sig_id = row["id"]
            else:
                cur.execute("""
                    INSERT INTO signals (run_id, type, target, strength, emitter_agent, created_at, last_reinforced_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (run_id, sig_type, target, initial_strength, emitter, now, now))
                sig_id = cur.lastrowid

            conn.commit()
            return Signal(
                id=sig_id,
                run_id=run_id,
                type=sig_type,
                target=target,
                strength=new_strength if row else initial_strength,
                emitter_agent=emitter,
                created_at=now,
                last_reinforced_at=now
            )

    def get_active_signals(self, run_id: str, decay_lambda: float = 0.01, min_threshold: float = 0.1) -> List[Signal]:
        """Fetch signals and apply exponential decay: strength *= exp(-lambda * dt)."""
        now = time.time()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM signals WHERE run_id = ?", (run_id,))
            rows = cur.fetchall()

            active = []
            for r in rows:
                dt = max(0.0, now - r["last_reinforced_at"])
                current_strength = r["strength"] * math.exp(-decay_lambda * dt)
                if current_strength >= min_threshold:
                    active.append(Signal(
                        id=r["id"],
                        run_id=r["run_id"],
                        type=r["type"],
                        target=r["target"],
                        strength=round(current_strength, 3),
                        emitter_agent=r["emitter_agent"],
                        created_at=r["created_at"],
                        last_reinforced_at=r["last_reinforced_at"]
                    ))
            return active

    def consume_signal(self, run_id: str, sig_type: str, target: Optional[str] = None):
        """Consume or clear a signal once acted upon by an agent."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            if target:
                cur.execute("DELETE FROM signals WHERE run_id = ? AND type = ? AND target = ?", (run_id, sig_type, target))
            else:
                cur.execute("DELETE FROM signals WHERE run_id = ? AND type = ?", (run_id, sig_type))
            conn.commit()
