# Stage 1: Blackboard + Single Qwen Agent Loop

## 1. Overview
Stage 1 establishes the decentralized foundation of the Swarm Website Builder:
1. **Blackboard Coordination Mechanism (`runtime/blackboard.py`)**: SQLite-backed shared memory implementing goals, tasks with atomic leases, artifacts with optimistic versioning, and stigmergic signals with exponential decay.
2. **Append-Only Event Log (`runtime/events.py`)**: Complete transactional trace of every swarm action, serving as the single source of truth for UI replaying and cursor tracking.
3. **Sandbox Workspace Isolation (`runtime/sandbox.py`, `runtime/tools.py`)**: Strict canonical path validation confining all file reads, writes, and listings to `.sandbox/<run_id>/`, with SHA-256 asset tracking and web asset integrity validation.
4. **Structured Qwen 3.5 Interface (`runtime/llm.py`)**: Async client with Pydantic JSON schema enforcement, automatic retry feedback loops (up to 2 retries), and hardware-aware request serialization (Semaphore = 1) protecting laptop GPU VRAM.
5. **Autonomous Worker Agent (`runtime/agent.py`)**: The Observe-Decide-Act-Report worker loop that seeds initial tasks, atomically claims tasks, writes complete code assets, and logs events.

---

## 2. Blackboard & Event Log Schemas

### SQLite Blackboard Tables
- `goals (run_id TEXT PRIMARY KEY, prompt TEXT, reference_image TEXT, created_at REAL)`
- `tasks (id TEXT, run_id TEXT, title TEXT, description TEXT, role_hint TEXT, status TEXT, owner TEXT, lease_expires_at REAL, depends_on TEXT, priority INT, target TEXT, created_at REAL, version INT, PRIMARY KEY(run_id, id))`
- `artifacts (id TEXT, run_id TEXT, path TEXT, content_hash TEXT, version INT, author_agent TEXT, created_at REAL, PRIMARY KEY(run_id, path))`
- `signals (id INT AUTOINCREMENT, run_id TEXT, type TEXT, target TEXT, strength REAL, emitter_agent TEXT, created_at REAL, last_reinforced_at REAL)`
- `scores (id INT AUTOINCREMENT, run_id TEXT, score_type TEXT, value REAL, iteration INT, created_at REAL)`

### Event Log Schema
- Schema: `(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, run_id TEXT, agent_id TEXT, event_type TEXT, target TEXT, payload TEXT)`
- Strict Event Types: `agent_spawned`, `task_claimed`, `file_edit`, `signal_emitted`, `test_run`, `test_failed`, `fix_applied`, `agent_failed`, `agent_recovered`, `task_done`.
- Export: Automatically exported to `runs/<run_id>/events.jsonl`.

---

## 3. Real Model Execution Verification (`qwen3.5:4b`)

### Run Details
- **Run ID**: `run_1794028907`
- **Model**: `qwen3.5:4b` (`d8b0f5e9760c`, 3.3 GB on Ollama)
- **Prompt**:
  > *"Build a modern responsive personal portfolio landing page for Alex Morgan, a Senior Full Stack Developer. Include a clean navbar, hero section with call-to-action, skills showcase (React, Python, Node, Docker), featured projects grid with preview cards, and a contact footer with social links. Use clean modern CSS with dark theme aesthetics."*
- **Hardware Profile**: Intel i5, RTX 4050 6GB Laptop GPU (100% GPU offload, peak VRAM ~3.7 GB, GPU temperature steady at 61°C).

### Autonomous Steps & Latencies
1. **Initial Task Seeding**:
   - Split goal prompt into 3 structured tasks: `task-01-structure` (HTML), `task-02-styling` (CSS), `task-03-script` (JavaScript).
   - Attempt 1 had empty output; retry loop kicked in with feedback and succeeded on Attempt 2 in 36.14s.
2. **Task Execution 1 (`task-03-script` -> `script.js`)**:
   - Generated 4,006 bytes of vanilla JavaScript (mobile menu toggle, smooth scroll behavior, card hover interactions).
   - Duration: 71.70s on Attempt 1.
3. **Task Execution 2 (`task-02-styling` -> `styles.css`)**:
   - Generated 7,554 bytes / 444 lines of dark-theme modern responsive CSS (custom properties, Inter font, cards, grid, buttons).
   - Retry triggered on unterminated string; succeeded on Attempt 2 in 178.19s.
4. **Task Execution 3 (`task-01-structure` -> `index.html`)**:
   - Generated 5,099 bytes / 140 lines of semantic HTML5 (`<!DOCTYPE html>`, navbar, hero, skills grid, project cards, footer).
   - Duration: 94.51s on Attempt 1.
5. **Completion**:
   - Agent observed no open tasks on blackboard.
   - Total execution duration: 780.25s.

### Asset Verification
- `verify_web_assets` status: **PASS**
- All required tags present: `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>`, `styles.css` linked, `script.js` linked.

---

## 4. Test Suite Verification
All 12 unit and integration tests passed cleanly:
```
tests/test_blackboard.py::test_atomic_claim_and_double_claim_prevention PASSED [  8%]
tests/test_blackboard.py::test_expired_lease_reopens_task PASSED         [ 16%]
tests/test_blackboard.py::test_artifact_optimistic_versioning PASSED     [ 25%]
tests/test_blackboard.py::test_signal_decay_and_reinforcement PASSED     [ 33%]
tests/test_events.py::test_append_and_retrieve_events PASSED             [ 41%]
tests/test_events.py::test_reject_invalid_event_type PASSED              [ 50%]
tests/test_events.py::test_incremental_streaming_since_id PASSED         [ 58%]
tests/test_events.py::test_export_jsonl PASSED                           [ 66%]
tests/test_sandbox.py::test_sandboxed_file_operations PASSED             [ 75%]
tests/test_sandbox.py::test_sandbox_security_traversal_rejection PASSED  [ 83%]
tests/test_sandbox.py::test_sandbox_cleanup PASSED                       [ 91%]
tests/test_stage1_e2e.py::test_stage1_agent_loop_end_to_end PASSED       [100%]
```

---

## 5. Deliverables & Artifacts
- Runtime files:
  - `runtime/blackboard.py`: Multi-zone SQLite blackboard.
  - `runtime/events.py`: Append-only event log.
  - `runtime/sandbox.py`: Isolated filesystem workspace.
  - `runtime/tools.py`: Sandboxed file manipulation & asset verifier.
  - `runtime/llm.py`: Schema-enforcing Qwen client with serialized GPU queue.
  - `runtime/agent.py`: Swarm agent worker loop.
  - `runtime/run_stage1.py`: Stage 1 end-to-end execution runner.
- Output artifacts:
  - Website sandbox: `.sandbox/run_1794028907/` (`index.html`, `styles.css`, `script.js`).
  - Run database & event trace: `runs/run_1794028907/blackboard.db`, `runs/run_1794028907/events.jsonl`.
