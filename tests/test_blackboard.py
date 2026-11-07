"""
Unit tests for SQLite Blackboard:
- Atomic claims under concurrency
- Lease expiration and automatic return to open
- Optimistic versioning on artifacts
- Signal decay and reinforcement math
"""

import os
import time
import pytest
from runtime.blackboard import Blackboard, Task, Signal


@pytest.fixture
def bb(tmp_path):
    db_file = tmp_path / "test_blackboard.db"
    return Blackboard(str(db_file))


def test_atomic_claim_and_double_claim_prevention(bb):
    run_id = "run-test-01"
    task = Task(
        id="t-001",
        run_id=run_id,
        title="Create Header",
        description="Build navbar",
        role_hint="Frontend",
        target="index.html"
    )
    bb.add_task(task)

    # First agent claims
    success1 = bb.claim_task_atomic(run_id, "t-001", "agent-frontend-1", lease_duration_sec=30.0)
    assert success1 is True

    # Second agent attempts to claim the same task -> MUST FAIL
    success2 = bb.claim_task_atomic(run_id, "t-001", "agent-frontend-2", lease_duration_sec=30.0)
    assert success2 is False

    # Check status and owner
    t = bb.get_task(run_id, "t-001")
    assert t.status == "claimed"
    assert t.owner == "agent-frontend-1"


def test_expired_lease_reopens_task(bb):
    run_id = "run-test-02"
    task = Task(
        id="t-002",
        run_id=run_id,
        title="Create Footer",
        description="Build footer",
        role_hint="Frontend"
    )
    bb.add_task(task)

    # Claim with a tiny 0.1s lease
    claimed = bb.claim_task_atomic(run_id, "t-002", "agent-stall", lease_duration_sec=0.1)
    assert claimed is True

    # Wait for lease to expire
    time.sleep(0.2)

    # Reopen expired leases
    reopened_count = bb.reopen_expired_leases(run_id)
    assert reopened_count == 1

    # Task should now be 'open' with no owner
    t = bb.get_task(run_id, "t-002")
    assert t.status == "open"
    assert t.owner is None

    # Another agent can now claim it
    recovered = bb.claim_task_atomic(run_id, "t-002", "agent-recovery", lease_duration_sec=30.0)
    assert recovered is True


def test_artifact_optimistic_versioning(bb):
    run_id = "run-test-03"
    path = "src/index.html"

    # Initial write v1
    art1 = bb.record_artifact(run_id, path, "hash1", "agent-1")
    assert art1.version == 1

    # Update based on v1 -> succeeds to v2
    art2 = bb.record_artifact(run_id, path, "hash2", "agent-2", expected_version=1)
    assert art2.version == 2

    # Stale update based on expected v1 -> MUST RAISE ERROR
    with pytest.raises(ValueError, match="Optimistic lock conflict"):
        bb.record_artifact(run_id, path, "hash3", "agent-3", expected_version=1)


def test_signal_decay_and_reinforcement(bb):
    run_id = "run-test-04"
    # Emit initial signal
    sig1 = bb.emit_signal(run_id, "need_styling", "hero", "agent-1", initial_strength=1.0)
    assert sig1.strength == 1.0

    # Reinforce by another agent
    sig2 = bb.emit_signal(run_id, "need_styling", "hero", "agent-2", initial_strength=1.5)
    assert sig2.strength == 2.5

    # Active signals check
    active = bb.get_active_signals(run_id, decay_lambda=0.01)
    assert len(active) == 1
    assert active[0].strength >= 2.4

