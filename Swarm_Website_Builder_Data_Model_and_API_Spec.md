# Swarm Website Builder: Data Model and API Specification

Version 1.0 | November 2026 | Status: Draft for mentor review
Derived from: Project Overview, sections 8, 10, 12 (blackboard schema, event schema, endpoints)

---

## 1. Purpose and scope

This document defines:

1. The **data model**: blackboard zones, event log, evaluation results and their relationships.
2. The **event schema**: the single source of truth for cursor visualization.
3. The **API**: REST endpoints and WebSocket streams exposed by the FastAPI layer.
4. The **coordination semantics** that the API and storage must guarantee (atomic claims, leases, versioning, signal decay).

Conventions:

- Storage: SQLite for development, PostgreSQL optional. Types below are portable. Where they differ, the PostgreSQL type is noted.
- IDs: ULIDs (sortable, 26 chars) stored as `TEXT`. Prefix shown in examples (`bld_`, `tsk_`, `agt_`).
- Timestamps: UTC, ISO 8601 in the API, `TEXT` or `TIMESTAMPTZ` in storage.
- JSON columns: `TEXT` in SQLite, `JSONB` in PostgreSQL.
- API base path: `/api/v1`. All bodies are JSON unless stated.

---

## 2. Entity overview

```
Build 1───* Task *───* Task (dependencies)
  │          │
  │          └──1 Agent (owner, via lease)
  │
  ├──* Artifact 1───* ArtifactVersion
  ├──* Signal
  ├──* Score
  ├──* Proposal 1───* Vote
  ├──* Event            (append-only log)
  ├──* Agent
  └──0..1 ReferenceImage

Experiment 1───* ExperimentRun *───1 Build
```

| Entity | Blackboard zone | Purpose |
| --- | --- | --- |
| Build | Goal | One user request (prompt or screenshot) and its overall state |
| ReferenceImage | Goal | Uploaded screenshot for screenshot-to-website mode |
| Task | Tasks | Unit of work with status, owner, dependencies, priority |
| Artifact, ArtifactVersion | Artifacts | Versioned files and specs produced by agents |
| Signal | Signals | Short messages with decaying strength |
| Score | Scores | Test results and visual similarity values |
| Proposal, Vote | Collective decisions | Design proposals and reviewer votes |
| Agent | Runtime | A Qwen 3.5 instance with role, memory and status |
| Event | Event log | Append-only record of every action |
| Experiment, ExperimentRun | Evaluation | Benchmark configurations and results |

---

## 3. Enumerations

| Enum | Values |
| --- | --- |
| `build_mode` | `prompt`, `screenshot` |
| `build_status` | `created`, `seeding`, `running`, `completed`, `failed`, `cancelled` |
| `agent_role` | `ui_ux`, `frontend`, `backend`, `database`, `testing`, `integration`, `reviewer` |
| `agent_status` | `idle`, `bidding`, `working`, `paused`, `failed`, `terminated` |
| `task_status` | `open`, `claimed`, `in_progress`, `in_review`, `done`, `failed` |
| `task_type` | `design`, `frontend`, `backend`, `database`, `test`, `bugfix`, `visual_fix`, `integration`, `review` |
| `artifact_kind` | `design_spec`, `html`, `css`, `js`, `jsx`, `api_route`, `schema`, `seed_data`, `config`, `asset`, `test_report`, `screenshot` |
| `signal_type` | `need_styling`, `bug_found`, `needs_review`, `blocked`, `conflict`, `ready_for_test`, `visual_mismatch`, `help_requested` |
| `score_kind` | `build_success`, `test_pass_rate`, `lighthouse_performance`, `lighthouse_accessibility`, `lighthouse_best_practices`, `visual_similarity` |
| `similarity_metric` | `ssim`, `phash` |
| `model_provider` | `ollama`, `llamacpp`, `hosted_qwen_plus` |
| `system_id` | `B1`, `B2`, `B3`, `S` |
| `failure_mode` | `kill`, `pause`, `stall` |
| `event_type` | see section 6.2 |

---

## 4. Data model (relational schema)

### 4.1 `builds`

One user request.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | TEXT | PK | `bld_<ulid>` |
| `mode` | TEXT | NOT NULL, enum `build_mode` | Prompt or screenshot |
| `prompt` | TEXT | NOT NULL | User goal in natural language |
| `parent_build_id` | TEXT | FK `builds.id`, NULL | Set on rebuild with a modified prompt (UC4) |
| `reference_image_id` | TEXT | FK `reference_images.id`, NULL | Required when `mode = screenshot` |
| `status` | TEXT | NOT NULL, enum `build_status` | Lifecycle state |
| `config` | JSON | NOT NULL | See 4.1.1 |
| `similarity_threshold` | REAL | NULL | Completion threshold for screenshot mode |
| `iteration_count` | INTEGER | NOT NULL, default 0 | Vision loop iterations used |
| `sandbox_path` | TEXT | NOT NULL | Temporary project folder |
| `system_id` | TEXT | NOT NULL, default `S` | `B1`, `B2`, `B3` or `S` (for benchmarks) |
| `seed` | INTEGER | NULL | Random seed for reproducibility |
| `created_at` | TIMESTAMP | NOT NULL | |
| `started_at` | TIMESTAMP | NULL | |
| `completed_at` | TIMESTAMP | NULL | |
| `failure_reason` | TEXT | NULL | Set when `status = failed` |

**4.1.1 `config` JSON**

```json
{
  "roles": ["ui_ux", "frontend", "backend", "testing"],
  "agent_count": 4,
  "models": {
    "simple": "qwen3.5:2b",
    "main": "qwen3.5:4b",
    "hard": "qwen3.5:9b",
    "hosted": null
  },
  "limits": {
    "max_iterations": 5,
    "max_tasks": 60,
    "lease_seconds": 90,
    "build_timeout_seconds": 1200
  },
  "signal": { "half_life_seconds": 60, "reinforce_factor": 0.5, "min_strength": 0.05 },
  "bidding": { "w_role": 0.5, "w_load": 0.2, "w_history": 0.3 },
  "seed": 42
}
```

Model names are placeholders. Verify the current Qwen 3.5 model list on Ollama or Hugging Face before use.

### 4.2 `reference_images`

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | TEXT | PK | `img_<ulid>` |
| `file_path` | TEXT | NOT NULL | Path inside the build's sandbox or upload folder |
| `mime_type` | TEXT | NOT NULL | `image/png`, `image/jpeg`, `image/webp` |
| `width` | INTEGER | NOT NULL | Pixels |
| `height` | INTEGER | NOT NULL | Pixels |
| `sha256` | TEXT | NOT NULL | Integrity and dedup |
| `created_at` | TIMESTAMP | NOT NULL | |

### 4.3 `agents`

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | TEXT | PK | `agt_<ulid>` |
| `build_id` | TEXT | FK `builds.id`, NOT NULL | |
| `role` | TEXT | NOT NULL, enum `agent_role` | |
| `display_name` | TEXT | NOT NULL | For example `Frontend-2` |
| `color` | TEXT | NOT NULL | Role color for the cursor (hex) |
| `status` | TEXT | NOT NULL, enum `agent_status` | |
| `model` | TEXT | NOT NULL | Model identifier used by this agent |
| `provider` | TEXT | NOT NULL, enum `model_provider` | |
| `current_task_id` | TEXT | FK `tasks.id`, NULL | |
| `replaces_agent_id` | TEXT | FK `agents.id`, NULL | Set when a replacement takes over (`agent_recovered`) |
| `memory` | JSON | NOT NULL, default `{}` | Short working memory (recent actions, notes) |
| `stats` | JSON | NOT NULL, default `{}` | Calls, tokens, tasks done, failures |
| `spawned_at` | TIMESTAMP | NOT NULL | |
| `last_heartbeat_at` | TIMESTAMP | NOT NULL | Used to detect stalls |
| `ended_at` | TIMESTAMP | NULL | |

Index: `(build_id, status)`.

### 4.4 `tasks`

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | TEXT | PK | `tsk_<ulid>` |
| `build_id` | TEXT | FK, NOT NULL | |
| `type` | TEXT | NOT NULL, enum `task_type` | |
| `title` | TEXT | NOT NULL | Short description |
| `description` | TEXT | NOT NULL | Full instructions for the agent |
| `target` | TEXT | NULL | Page section or file the task affects (drives the cursor position) |
| `preferred_role` | TEXT | NULL, enum `agent_role` | Used in bid role match |
| `status` | TEXT | NOT NULL, enum `task_status` | |
| `priority` | INTEGER | NOT NULL, default 50 | 0 to 100, higher first |
| `owner_agent_id` | TEXT | FK `agents.id`, NULL | Set while claimed |
| `lease_expires_at` | TIMESTAMP | NULL | Lease timeout |
| `attempt_count` | INTEGER | NOT NULL, default 0 | Incremented on each claim |
| `max_attempts` | INTEGER | NOT NULL, default 3 | Task moves to `failed` after this many expired or failed attempts |
| `created_by_agent_id` | TEXT | FK `agents.id`, NULL | NULL when created by the seeding step |
| `source_signal_id` | TEXT | FK `signals.id`, NULL | Signal that caused this task (for example a bug) |
| `result_summary` | TEXT | NULL | Short outcome text |
| `version` | INTEGER | NOT NULL, default 1 | Optimistic concurrency counter |
| `created_at` | TIMESTAMP | NOT NULL | |
| `updated_at` | TIMESTAMP | NOT NULL | |
| `completed_at` | TIMESTAMP | NULL | |

Indexes: `(build_id, status, priority DESC)`, `(lease_expires_at) WHERE status IN ('claimed','in_progress')`.

**Task dependencies**

`task_dependencies`

| Column | Type | Constraints |
| --- | --- | --- |
| `task_id` | TEXT | FK `tasks.id`, PK part |
| `depends_on_task_id` | TEXT | FK `tasks.id`, PK part |

A task is **biddable** only when it is `open` and every dependency is `done`.

### 4.5 `artifacts` and `artifact_versions`

`artifacts` is the logical file. `artifact_versions` holds each saved content version (optimistic versioning).

`artifacts`

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | TEXT | PK | `art_<ulid>` |
| `build_id` | TEXT | FK, NOT NULL | |
| `kind` | TEXT | NOT NULL, enum `artifact_kind` | |
| `path` | TEXT | NOT NULL | Relative path in the sandbox, for example `src/pages/index.html` |
| `latest_version` | INTEGER | NOT NULL | Current version number |
| `locked_by_conflict` | BOOLEAN | NOT NULL, default false | True while a `conflict` signal is unresolved |
| `created_at` | TIMESTAMP | NOT NULL | |
| `updated_at` | TIMESTAMP | NOT NULL | |

Unique: `(build_id, path)`.

`artifact_versions`

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | TEXT | PK | `arv_<ulid>` |
| `artifact_id` | TEXT | FK, NOT NULL | |
| `version` | INTEGER | NOT NULL | 1, 2, 3, ... |
| `content` | TEXT | NULL | Text content. NULL for binary assets |
| `content_path` | TEXT | NULL | File path for binary assets |
| `content_sha256` | TEXT | NOT NULL | |
| `author_agent_id` | TEXT | FK `agents.id`, NOT NULL | |
| `task_id` | TEXT | FK `tasks.id`, NULL | Task that produced this version |
| `base_version` | INTEGER | NOT NULL | Version the author read before editing |
| `merged_from` | JSON | NULL | Version numbers merged by the Integration agent |
| `created_at` | TIMESTAMP | NOT NULL | |

Unique: `(artifact_id, version)`.

**Write rule:** a write succeeds only if `base_version = artifacts.latest_version`. Otherwise the API returns `409 VERSION_CONFLICT` and the runtime posts a `conflict` signal (see 5.3).

### 4.6 `signals`

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | TEXT | PK | `sig_<ulid>` |
| `build_id` | TEXT | FK, NOT NULL | |
| `type` | TEXT | NOT NULL, enum `signal_type` | |
| `target` | TEXT | NULL | Section, file or task the signal concerns |
| `message` | TEXT | NULL | Short free text (max 280 chars) |
| `base_strength` | REAL | NOT NULL | Strength at last reinforcement (0 to 1) |
| `last_reinforced_at` | TIMESTAMP | NOT NULL | Decay starts here |
| `emitter_count` | INTEGER | NOT NULL, default 1 | Distinct agents that emitted it |
| `emitted_by` | JSON | NOT NULL | List of agent ids |
| `resolved` | BOOLEAN | NOT NULL, default false | |
| `resolved_by_task_id` | TEXT | FK `tasks.id`, NULL | |
| `created_at` | TIMESTAMP | NOT NULL | |

Index: `(build_id, resolved, type, target)`.

**Effective strength** (computed on read, not stored):

```
strength(t) = base_strength * 0.5 ^ ((t - last_reinforced_at) / half_life_seconds)
```

**Reinforcement:** when an agent emits a signal with the same `(build_id, type, target)` as an unresolved signal, the existing row is updated:

```
base_strength = min(1.0, strength(now) + reinforce_factor * (1 - strength(now)))
last_reinforced_at = now
emitter_count += 1
```

Signals with `strength < min_strength` are treated as expired and ignored by agents.

### 4.7 `scores`

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | TEXT | PK | `scr_<ulid>` |
| `build_id` | TEXT | FK, NOT NULL | |
| `kind` | TEXT | NOT NULL, enum `score_kind` | |
| `value` | REAL | NOT NULL | 0 to 1 for rates and similarity, 0 to 100 for Lighthouse |
| `metric` | TEXT | NULL, enum `similarity_metric` | For `visual_similarity` |
| `iteration` | INTEGER | NOT NULL, default 0 | Vision loop iteration |
| `details` | JSON | NULL | Failed tests, per-section similarity, raw Lighthouse output |
| `agent_id` | TEXT | FK `agents.id`, NOT NULL | Usually the Testing agent |
| `created_at` | TIMESTAMP | NOT NULL | |

### 4.8 `proposals` and `votes`

Used for collective design decisions.

`proposals`

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | TEXT | PK | `prp_<ulid>` |
| `build_id` | TEXT | FK, NOT NULL | |
| `topic` | TEXT | NOT NULL | For example `color_palette`, `layout` |
| `author_agent_id` | TEXT | FK, NOT NULL | |
| `artifact_version_id` | TEXT | FK, NULL | Proposed content |
| `summary` | TEXT | NOT NULL | |
| `status` | TEXT | NOT NULL | `open`, `selected`, `rejected`, `merged` |
| `created_at` | TIMESTAMP | NOT NULL | |

`votes`

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | TEXT | PK | |
| `proposal_id` | TEXT | FK, NOT NULL | |
| `voter_agent_id` | TEXT | FK, NOT NULL | Reviewer agent |
| `value` | INTEGER | NOT NULL | `-1`, `0`, `+1` |
| `critique` | TEXT | NULL | Short written critique |
| `created_at` | TIMESTAMP | NOT NULL | |

Unique: `(proposal_id, voter_agent_id)`. The proposal with the highest vote sum for a topic is selected once all assigned reviewers have voted or a timeout passes.

### 4.9 `bids` (optional, for analysis)

Bids can be kept in memory during a build. Persisting them supports analysis of allocation behavior.

| Column | Type | Description |
| --- | --- | --- |
| `id` | TEXT PK | |
| `task_id` | TEXT FK | |
| `agent_id` | TEXT FK | |
| `value` | REAL | Bid value |
| `components` | JSON | `{ "role_match": 1.0, "load": 0.2, "history": 0.7 }` |
| `won` | BOOLEAN | |
| `created_at` | TIMESTAMP | |

**Bid formula (default):**

```
bid = w_role * role_match + w_history * past_success - w_load * current_load
```

- `role_match`: 1.0 if `task.preferred_role = agent.role`, 0.3 if the agent can act as a fallback, else 0.
- `past_success`: success rate on tasks of the same `type`, from `agents.stats`.
- `current_load`: normalized count of tasks owned by the agent (0 or 1 in the single-task case).

### 4.10 `events` (append-only)

The event log is the **single source of truth** for visualization and analysis. Rows are never updated or deleted during a build.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `seq` | INTEGER | PK, autoincrement | Global order. Used for replay and WebSocket resume |
| `id` | TEXT | UNIQUE | `evt_<ulid>` |
| `build_id` | TEXT | FK, NOT NULL | |
| `ts` | TIMESTAMP | NOT NULL | Event time, millisecond precision |
| `agent_id` | TEXT | FK `agents.id`, NULL | NULL for system events |
| `type` | TEXT | NOT NULL, enum `event_type` | |
| `target` | TEXT | NULL | Section id or file path |
| `payload` | JSON | NOT NULL, default `{}` | Type-specific fields (section 6.3) |

Indexes: `(build_id, seq)`, `(build_id, type)`.

### 4.11 `experiments` and `experiment_runs`

`experiments`

| Column | Type | Description |
| --- | --- | --- |
| `id` | TEXT PK | `exp_<ulid>` |
| `code` | TEXT | `E1`, `E2`, `E3`, `E4` |
| `name` | TEXT | Human name |
| `research_question` | TEXT | `RQ1` to `RQ4` |
| `systems` | JSON | List of `system_id` values compared |
| `test_set` | JSON | Prompt ids and screenshot ids used |
| `repetitions` | INTEGER | At least 3 |
| `failure_injection` | JSON | NULL, or `{ "mode": "kill", "count": 1, "at_progress": 0.5 }` |
| `vision_loop_enabled` | BOOLEAN | For E4 |
| `status` | TEXT | `created`, `running`, `completed`, `failed` |
| `created_at` | TIMESTAMP | |

`experiment_runs`

| Column | Type | Description |
| --- | --- | --- |
| `id` | TEXT PK | `run_<ulid>` |
| `experiment_id` | TEXT FK | |
| `build_id` | TEXT FK | Build created for this run |
| `system_id` | TEXT | `B1`, `B2`, `B3`, `S` |
| `test_case_id` | TEXT | Prompt or screenshot id |
| `repetition` | INTEGER | 1, 2, 3, ... |
| `metrics` | JSON | See 4.11.1 |
| `created_at` | TIMESTAMP | |

**4.11.1 `metrics` JSON**

```json
{
  "build_success": true,
  "test_pass_rate": 0.92,
  "lighthouse": { "performance": 88, "accessibility": 95, "best_practices": 100 },
  "visual_similarity": { "metric": "ssim", "value": 0.81 },
  "total_seconds": 214.6,
  "model_calls": 143,
  "tokens_in": 91200,
  "tokens_out": 48800,
  "bugs_found": 7,
  "bugs_fixed": 6,
  "recovery": { "injected": true, "recovery_seconds": 18.2, "completed": true }
}
```

---

## 5. Coordination semantics

These guarantees must hold regardless of how the runtime is implemented.

### 5.1 Task lifecycle

```
          claim              start              submit
 open ──────────► claimed ──────────► in_progress ─────────► in_review ──► done
  ▲                  │                    │                      │
  │   lease expiry   │    lease expiry    │       rejected       │
  └──────────────────┴────────────────────┴──────────────────────┘
                                          │
                              attempts >= max_attempts
                                          ▼
                                        failed
```

- `claimed` and `in_progress` always have `owner_agent_id` and `lease_expires_at`.
- Tasks that need no review go from `in_progress` directly to `done`.
- Expiry or agent failure returns the task to `open`, clears the owner, increments nothing further, and emits `lease_expired`.
- When `attempt_count >= max_attempts`, the task becomes `failed` and a `blocked` signal is emitted.

### 5.2 Atomic claim

A claim must be a single conditional update, so two agents never hold one task:

```sql
UPDATE tasks
SET status = 'claimed',
    owner_agent_id = :agent_id,
    lease_expires_at = :now + :lease_seconds,
    attempt_count = attempt_count + 1,
    version = version + 1,
    updated_at = :now
WHERE id = :task_id
  AND status = 'open'
  AND version = :expected_version;
```

If zero rows are updated, the claim fails with `409 TASK_ALREADY_CLAIMED`.

For bid resolution, the runtime collects bids for a task during a short window (default 500 ms), picks the highest bid (ties broken by earliest bid, then lowest agent id) and only that agent is allowed to call the claim endpoint successfully.

### 5.3 Leases

- Lease length defaults to 90 seconds (`config.limits.lease_seconds`).
- The owner extends the lease with a **heartbeat** (`POST .../heartbeat`). Each heartbeat adds a full lease period from now, up to a maximum total of 10 minutes per claim.
- A background reaper runs every 5 seconds. For each task whose `lease_expires_at < now`, it sets `status = 'open'`, clears the owner, and emits `lease_expired`, then `agent_failed` if the agent heartbeat is also stale.

### 5.4 Optimistic versioning for artifacts

1. Agent reads artifact at version `N`.
2. Agent submits a new version with `base_version = N`.
3. If `latest_version = N`, the write is accepted and becomes `N + 1`.
4. If `latest_version > N`, the write is rejected with `409 VERSION_CONFLICT`. The runtime emits a `conflict` signal and creates an `integration` task. The Integration agent merges, writes version `N + k` with `merged_from` set, and resolves the signal.

### 5.5 Completion criteria

A build moves to `completed` when all are true:

1. No task has status other than `done` (or `failed` tasks are explicitly waived by config).
2. The latest `build_success` score is 1.
3. The latest `test_pass_rate` score is 1.0 (or above `config.limits.min_test_pass_rate`).
4. No unresolved signal of type `bug_found` has effective strength above `min_strength`.
5. Screenshot mode only: the latest `visual_similarity` is at or above `similarity_threshold`, **or** `iteration_count >= max_iterations`.

If criteria are not met when no open tasks remain, the Testing agent posts new fix tasks. If the build timeout passes, the build becomes `failed` with `failure_reason = "timeout"`.

---

## 6. Event schema

### 6.1 Envelope

Every event, in the database, over WebSocket, and in exports, has this shape:

```json
{
  "seq": 1042,
  "id": "evt_01JC8Z...",
  "build_id": "bld_01JC8Y...",
  "ts": "2026-11-06T14:21:09.317Z",
  "agent_id": "agt_01JC8Z...",
  "type": "task_claimed",
  "target": "section:hero",
  "payload": { "task_id": "tsk_01JC8Z...", "bid": 0.74 }
}
```

`target` uses these formats:

| Format | Example | Meaning |
| --- | --- | --- |
| `section:<name>` | `section:hero` | A section of the preview page |
| `file:<path>` | `file:src/pages/index.html` | A file in the sandbox |
| `panel:<name>` | `panel:tests` | An interface panel (`tests`, `preview`, `log`) |
| `task:<id>` | `task:tsk_01...` | A task |

### 6.2 Event types

Cursor behavior is taken from the project overview (section 12). Additional system events do not move cursors.

| Event type | Cursor behavior | Emitted by |
| --- | --- | --- |
| `build_created` | None | API |
| `build_started` | None | Runtime |
| `build_completed` | Progress bar to 100% | Runtime |
| `build_failed` | Error banner | Runtime |
| `agent_spawned` | Cursor appears with the role color | Runtime |
| `agent_heartbeat` | None (not persisted by default, see 6.4) | Agent |
| `task_created` | Card appears on task board | Agent or seeding step |
| `bid_placed` | None (optional ghost marker) | Agent |
| `task_claimed` | Cursor moves to the page section the task targets | Agent |
| `task_started` | Card moves to in progress | Agent |
| `file_edit` | Cursor shows typing or highlight on that section | Agent |
| `artifact_written` | None (updates file tree) | Runtime |
| `signal_emitted` | A short pulse or trail appears at the target | Agent |
| `signal_reinforced` | Pulse intensity increases | Runtime |
| `signal_resolved` | Pulse removed | Agent |
| `proposal_posted` | Proposal card appears | Agent |
| `vote_cast` | Reviewer cursor pulses on proposal | Agent |
| `proposal_selected` | Winning proposal highlighted | Runtime |
| `conflict_detected` | Section outlined in orange | Runtime |
| `test_run` | Cursor moves to the test panel or preview | Agent |
| `test_failed` | Target section flashes red | Agent |
| `fix_applied` | Target section flashes green | Agent |
| `score_recorded` | Score dashboard updates | Agent |
| `lease_expired` | Task card shows a warning, returns to open | Runtime |
| `agent_failed` | Cursor fades out and a failure marker is shown | Runtime |
| `agent_recovered` | A replacement cursor takes over the task | Runtime |
| `agent_paused` / `agent_resumed` | Cursor dims / restores | Runtime |
| `failure_injected` | Marker on the agent (for experiments) | API |
| `task_done` | Section is marked complete and progress updates | Agent |
| `task_failed` | Card turns red | Runtime |

### 6.3 Payload definitions

| Event type | Required payload fields |
| --- | --- |
| `build_created` | `mode`, `prompt_preview` |
| `agent_spawned` | `role`, `display_name`, `color`, `model` |
| `task_created` | `task_id`, `title`, `type`, `priority`, `depends_on` |
| `bid_placed` | `task_id`, `bid`, `components` |
| `task_claimed` | `task_id`, `bid`, `lease_expires_at`, `attempt` |
| `file_edit` | `artifact_id`, `path`, `version`, `lines_added`, `lines_removed`, `summary` |
| `artifact_written` | `artifact_id`, `path`, `version`, `base_version`, `sha256` |
| `signal_emitted` | `signal_id`, `signal_type`, `strength`, `message` |
| `signal_reinforced` | `signal_id`, `strength`, `emitter_count` |
| `signal_resolved` | `signal_id`, `resolved_by_task_id` |
| `proposal_posted` | `proposal_id`, `topic`, `summary` |
| `vote_cast` | `proposal_id`, `value` |
| `conflict_detected` | `artifact_id`, `path`, `versions` |
| `test_run` | `suite` (`build`, `unit`, `e2e`, `lighthouse`, `visual`), `iteration` |
| `test_failed` | `suite`, `failures` (list of `{ "name", "message", "target" }`) |
| `fix_applied` | `task_id`, `fixed_signal_id`, `artifact_id`, `version` |
| `score_recorded` | `score_id`, `kind`, `value`, `iteration` |
| `lease_expired` | `task_id`, `previous_owner_agent_id`, `attempt` |
| `agent_failed` | `reason` (`killed`, `stalled`, `error`), `task_id` |
| `agent_recovered` | `replaces_agent_id`, `task_id` |
| `failure_injected` | `mode`, `injected_by` |
| `task_done` | `task_id`, `result_summary`, `progress` (0 to 1) |
| `task_failed` | `task_id`, `reason`, `attempts` |

### 6.4 Logging rules

- Every event is persisted except `agent_heartbeat`, which is stored only in `agents.last_heartbeat_at`.
- Events within a build are strictly ordered by `seq`.
- Payloads should stay under 4 KB. File contents are never put in payloads, only references.
- Each LLM call is recorded as a separate non-visual event type `model_call` (fields: `model`, `tokens_in`, `tokens_out`, `latency_ms`, `purpose`) so cost metrics in section 4.11.1 can be computed from the log. It does not move cursors.

---

## 7. REST API

### 7.1 General rules

- Base URL: `http://localhost:8000/api/v1`
- Content type: `application/json`, except uploads (`multipart/form-data`).
- Authentication: none in the local development version (multi-user accounts are out of scope). Add an `X-API-Key` header if the API is ever exposed beyond localhost.
- Pagination: `?limit=` (default 50, max 200) and `?cursor=` (opaque). Responses include `next_cursor` or `null`.
- Filtering: query parameters named after fields (for example `?status=open&role=frontend`).
- Idempotency: `POST` endpoints that create builds accept an optional `Idempotency-Key` header.

### 7.2 Error format

```json
{
  "error": {
    "code": "TASK_ALREADY_CLAIMED",
    "message": "Task tsk_01JC8Z... is no longer open.",
    "details": { "current_status": "claimed", "owner_agent_id": "agt_01..." }
  }
}
```

| HTTP | Code | When |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | Body or query failed validation |
| 400 | `INVALID_IMAGE` | Unsupported type, corrupt file or too large |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `TASK_ALREADY_CLAIMED` | Atomic claim failed |
| 409 | `VERSION_CONFLICT` | `base_version` is stale |
| 409 | `INVALID_STATE` | Action not allowed in the current state (for example claiming a task with unmet dependencies) |
| 409 | `LEASE_EXPIRED` | Heartbeat or submit after the lease ended |
| 403 | `NOT_OWNER` | Agent does not own the task |
| 413 | `PAYLOAD_TOO_LARGE` | Upload or artifact exceeds the limit |
| 422 | `MODEL_OUTPUT_INVALID` | Agent action JSON failed schema validation |
| 429 | `RATE_LIMITED` | Too many requests |
| 503 | `MODEL_UNAVAILABLE` | Ollama or llama.cpp is not reachable |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

### 7.3 Builds

| Method | Path | Description |
| --- | --- | --- |
| POST | `/builds` | Create and start a build (UC1, UC2) |
| GET | `/builds` | List builds |
| GET | `/builds/{build_id}` | Get a build with summary counts |
| POST | `/builds/{build_id}/rebuild` | Rebuild with a modified prompt (UC4) |
| POST | `/builds/{build_id}/cancel` | Cancel a running build |
| GET | `/builds/{build_id}/progress` | Progress snapshot |
| GET | `/builds/{build_id}/export` | Download the generated project as a ZIP |

**POST `/builds`**

Prompt mode (JSON):

```json
{
  "mode": "prompt",
  "prompt": "A portfolio website for a photographer with a gallery and contact form",
  "config": { "roles": ["ui_ux", "frontend", "backend", "testing"], "seed": 42 }
}
```

Screenshot mode (`multipart/form-data`): fields `mode=screenshot`, `prompt` (optional extra instructions), `image` (file), `config` (JSON string), `similarity_threshold` (default 0.85).

Response `201`:

```json
{
  "id": "bld_01JC8Y...",
  "mode": "prompt",
  "status": "seeding",
  "created_at": "2026-11-06T14:20:00Z",
  "links": {
    "events_ws": "/api/v1/builds/bld_01JC8Y.../events/stream",
    "preview": "/api/v1/builds/bld_01JC8Y.../preview/"
  }
}
```

**GET `/builds/{build_id}/progress`**

```json
{
  "build_id": "bld_01JC8Y...",
  "status": "running",
  "progress": 0.58,
  "tasks": { "open": 3, "claimed": 1, "in_progress": 2, "in_review": 0, "done": 11, "failed": 0 },
  "agents": { "idle": 1, "working": 3, "failed": 0 },
  "iteration": 2,
  "latest_scores": { "test_pass_rate": 0.8, "visual_similarity": 0.74 },
  "elapsed_seconds": 96.4
}
```

`progress` is `done_tasks / total_tasks`, adjusted so it cannot reach 1.0 until completion criteria pass.

**POST `/builds/{build_id}/rebuild`**

```json
{ "prompt": "Same site, but dark theme and add a pricing page", "reuse_artifacts": true }
```

Creates a new build with `parent_build_id` set. If `reuse_artifacts` is true, the latest artifact versions are copied into the new build as version 1.

### 7.4 Agents

| Method | Path | Description |
| --- | --- | --- |
| GET | `/builds/{build_id}/agents` | List agents with status |
| GET | `/builds/{build_id}/agents/{agent_id}` | Agent detail (UC3): current task, recent actions, stats |
| POST | `/builds/{build_id}/agents/{agent_id}/inject-failure` | Kill, pause or stall an agent (UC6, FR11) |
| POST | `/builds/{build_id}/agents/{agent_id}/resume` | Resume a paused agent |

**GET `/builds/{build_id}/agents/{agent_id}`**

```json
{
  "id": "agt_01JC8Z...",
  "role": "frontend",
  "display_name": "Frontend-1",
  "color": "#3B82F6",
  "status": "working",
  "model": "qwen3.5:4b",
  "current_task": {
    "id": "tsk_01JC90...",
    "title": "Build hero section",
    "target": "section:hero",
    "lease_expires_at": "2026-11-06T14:22:40Z"
  },
  "recent_actions": [
    { "seq": 1040, "type": "task_claimed", "target": "section:hero", "ts": "2026-11-06T14:21:09.317Z" },
    { "seq": 1041, "type": "file_edit", "target": "file:src/pages/index.html", "ts": "2026-11-06T14:21:14.002Z" }
  ],
  "stats": { "tasks_done": 4, "model_calls": 22, "tokens_in": 15800, "tokens_out": 9300 }
}
```

**POST `.../inject-failure`**

```json
{ "mode": "kill" }
```

`mode` is one of `kill` (agent stops immediately, lease expires naturally), `pause` (agent stops heartbeating until resumed), `stall` (agent holds its lease but makes no progress). Emits `failure_injected` and later `agent_failed`, `lease_expired`, `agent_recovered`.

### 7.5 Tasks

| Method | Path | Description |
| --- | --- | --- |
| GET | `/builds/{build_id}/tasks` | List tasks. Filters: `status`, `type`, `owner_agent_id` |
| GET | `/builds/{build_id}/tasks/{task_id}` | Task detail |
| POST | `/builds/{build_id}/tasks` | Create a task (agents or seeding step) |
| POST | `/builds/{build_id}/tasks/{task_id}/bids` | Place a bid |
| POST | `/builds/{build_id}/tasks/{task_id}/claim` | Claim a task (atomic) |
| POST | `/builds/{build_id}/tasks/{task_id}/start` | Mark as in progress |
| POST | `/builds/{build_id}/tasks/{task_id}/heartbeat` | Extend the lease |
| POST | `/builds/{build_id}/tasks/{task_id}/submit` | Submit work for review or completion |
| POST | `/builds/{build_id}/tasks/{task_id}/release` | Voluntarily give the task back |
| POST | `/builds/{build_id}/tasks/{task_id}/fail` | Report that the attempt failed |

The agent-facing endpoints (bids, claim, start, heartbeat, submit, release, fail) are used by the swarm runtime. They are documented because the runtime can run as a separate process and because they define the contract for coordination. They are not used by the web interface.

**POST `/builds/{build_id}/tasks`**

```json
{
  "type": "frontend",
  "title": "Build hero section",
  "description": "Create the hero with headline, subtitle and call-to-action button using the design tokens.",
  "target": "section:hero",
  "preferred_role": "frontend",
  "priority": 80,
  "depends_on": ["tsk_01JC8Z..."],
  "created_by_agent_id": "agt_01JC8Z...",
  "source_signal_id": null
}
```

**POST `.../bids`**

```json
{
  "agent_id": "agt_01JC8Z...",
  "value": 0.74,
  "components": { "role_match": 1.0, "load": 0.0, "history": 0.7 }
}
```

Response `202`: `{ "accepted": true, "window_closes_at": "2026-11-06T14:21:09.800Z" }`.

**POST `.../claim`**

```json
{ "agent_id": "agt_01JC8Z...", "expected_version": 3 }
```

Response `200`:

```json
{
  "task_id": "tsk_01JC90...",
  "status": "claimed",
  "owner_agent_id": "agt_01JC8Z...",
  "lease_expires_at": "2026-11-06T14:22:39Z",
  "attempt_count": 1,
  "version": 4
}
```

Errors: `409 TASK_ALREADY_CLAIMED`, `409 INVALID_STATE` (dependencies unmet), `403 NOT_OWNER` (agent lost the bid window).

**POST `.../submit`**

```json
{
  "agent_id": "agt_01JC8Z...",
  "result_summary": "Hero section built with responsive layout.",
  "requires_review": false,
  "artifact_version_ids": ["arv_01JC91..."]
}
```

If `requires_review` is true the task becomes `in_review` and a `needs_review` signal is emitted. Otherwise the task becomes `done` and `task_done` is emitted.

### 7.6 Artifacts

| Method | Path | Description |
| --- | --- | --- |
| GET | `/builds/{build_id}/artifacts` | List artifacts (file tree). Filter: `kind`, `path_prefix` |
| GET | `/builds/{build_id}/artifacts/{artifact_id}` | Artifact metadata and latest content |
| GET | `/builds/{build_id}/artifacts/{artifact_id}/versions` | Version history |
| GET | `/builds/{build_id}/artifacts/{artifact_id}/versions/{version}` | Content of one version |
| PUT | `/builds/{build_id}/artifacts` | Create or update an artifact (optimistic versioning) |

**PUT `/builds/{build_id}/artifacts`**

```json
{
  "agent_id": "agt_01JC8Z...",
  "task_id": "tsk_01JC90...",
  "path": "src/pages/index.html",
  "kind": "html",
  "content": "<!doctype html>...",
  "base_version": 2
}
```

For a new file, send `base_version: 0`. Response `200`:

```json
{ "artifact_id": "art_01JC92...", "version": 3, "sha256": "9f2b...", "status": "accepted" }
```

On stale `base_version`, the response is `409 VERSION_CONFLICT` with `details: { "latest_version": 4 }`.

Constraints: path must be relative, must not contain `..`, and must stay inside the sandbox. Maximum content size 512 KB (text).

### 7.7 Signals

| Method | Path | Description |
| --- | --- | --- |
| GET | `/builds/{build_id}/signals` | List signals with effective strength. Filters: `type`, `resolved`, `min_strength` |
| POST | `/builds/{build_id}/signals` | Emit or reinforce a signal |
| POST | `/builds/{build_id}/signals/{signal_id}/resolve` | Mark a signal as resolved |

**POST `/builds/{build_id}/signals`**

```json
{
  "agent_id": "agt_01JC8Z...",
  "type": "bug_found",
  "target": "section:contact-form",
  "message": "Submit button does not post to /api/contact.",
  "strength": 0.8
}
```

Response `201` (new) or `200` (reinforced):

```json
{
  "id": "sig_01JC93...",
  "type": "bug_found",
  "target": "section:contact-form",
  "strength": 0.8,
  "emitter_count": 1,
  "reinforced": false
}
```

### 7.8 Scores

| Method | Path | Description |
| --- | --- | --- |
| GET | `/builds/{build_id}/scores` | List scores. Filters: `kind`, `iteration` |
| POST | `/builds/{build_id}/scores` | Record a score (Testing agent) |
| GET | `/builds/{build_id}/scores/visual-history` | Visual similarity by iteration (RQ4 chart data) |

**POST `/builds/{build_id}/scores`**

```json
{
  "agent_id": "agt_01JC95...",
  "kind": "visual_similarity",
  "metric": "ssim",
  "value": 0.81,
  "iteration": 2,
  "details": { "sections": { "hero": 0.9, "footer": 0.6 } }
}
```

### 7.9 Proposals and votes

| Method | Path | Description |
| --- | --- | --- |
| GET | `/builds/{build_id}/proposals` | List proposals with vote totals |
| POST | `/builds/{build_id}/proposals` | Post a proposal |
| POST | `/builds/{build_id}/proposals/{proposal_id}/votes` | Cast a vote (one per reviewer) |

**POST `.../votes`**

```json
{ "voter_agent_id": "agt_01JC96...", "value": 1, "critique": "Palette meets contrast requirements." }
```

### 7.10 Events and replay

| Method | Path | Description |
| --- | --- | --- |
| GET | `/builds/{build_id}/events` | Paginated event history. Filters: `type`, `agent_id`, `since_seq`, `until_seq` |
| GET | `/builds/{build_id}/events/export` | Full log as NDJSON (one event per line) |
| WS | `/builds/{build_id}/events/stream` | Live event stream (see section 8) |

**GET `/builds/{build_id}/events?since_seq=1000&limit=2`**

```json
{
  "items": [
    { "seq": 1001, "id": "evt_01...", "build_id": "bld_01...", "ts": "2026-11-06T14:21:01.100Z", "agent_id": "agt_01...", "type": "task_claimed", "target": "section:nav", "payload": { "task_id": "tsk_01...", "bid": 0.71 } },
    { "seq": 1002, "id": "evt_01...", "build_id": "bld_01...", "ts": "2026-11-06T14:21:02.540Z", "agent_id": "agt_01...", "type": "file_edit", "target": "file:src/components/Nav.jsx", "payload": { "path": "src/components/Nav.jsx", "version": 1 } }
  ],
  "next_cursor": "1002"
}
```

### 7.11 Preview

| Method | Path | Description |
| --- | --- | --- |
| GET | `/builds/{build_id}/preview/` | Serves the generated site's `index.html` from the sandbox |
| GET | `/builds/{build_id}/preview/{path}` | Serves other generated files |
| GET | `/builds/{build_id}/screenshot` | Latest preview screenshot (PNG). Query: `iteration` |
| GET | `/builds/{build_id}/reference-image` | The uploaded reference screenshot |

Preview responses set `Content-Security-Policy: sandbox allow-scripts` and are served without cookies, so generated code cannot reach the interface or personal files.

### 7.12 Evaluation

| Method | Path | Description |
| --- | --- | --- |
| GET | `/experiments` | List experiments |
| POST | `/experiments` | Create an experiment (UC5) |
| GET | `/experiments/{experiment_id}` | Experiment detail and status |
| POST | `/experiments/{experiment_id}/run` | Start all runs |
| POST | `/experiments/{experiment_id}/cancel` | Cancel |
| GET | `/experiments/{experiment_id}/runs` | List runs with metrics |
| GET | `/experiments/{experiment_id}/summary` | Aggregated means and standard deviations per system |
| GET | `/experiments/{experiment_id}/export` | Results as CSV or JSON. Query: `format=csv|json` |

**POST `/experiments`** (example for E3, failure injection)

```json
{
  "code": "E3",
  "name": "Kill one agent mid-build",
  "research_question": "RQ3",
  "systems": ["S"],
  "test_set": { "prompts": ["p03_landing", "p07_blog"], "screenshots": [] },
  "repetitions": 3,
  "failure_injection": { "mode": "kill", "count": 1, "at_progress": 0.5 },
  "vision_loop_enabled": false
}
```

**GET `/experiments/{id}/summary`**

```json
{
  "experiment_id": "exp_01JC97...",
  "systems": {
    "B1": { "runs": 30, "build_success_rate": 0.70, "test_pass_rate": { "mean": 0.61, "sd": 0.14 }, "total_seconds": { "mean": 55.0, "sd": 9.2 } },
    "S":  { "runs": 30, "build_success_rate": 0.90, "test_pass_rate": { "mean": 0.84, "sd": 0.09 }, "total_seconds": { "mean": 210.3, "sd": 41.7 } }
  }
}
```

The numbers above are illustrative only, not results.

### 7.13 System

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness: API, database, model server status |
| GET | `/models` | Models available from Ollama or llama.cpp, and which are loaded |
| GET | `/config/defaults` | Default build configuration |

---

## 8. WebSocket API

### 8.1 Event stream

`WS /api/v1/builds/{build_id}/events/stream`

Query parameters:

| Parameter | Description |
| --- | --- |
| `since_seq` | Resume after this sequence number. The server first replays missed events, then streams live ones |
| `types` | Optional comma-separated filter of event types |
| `speed` | Replay mode only: playback speed multiplier (for example `4`) |
| `replay` | `true` to replay a finished build from the log instead of following live |

Server to client messages:

```json
{ "kind": "event", "event": { "seq": 1042, "type": "task_claimed", "...": "..." } }
{ "kind": "snapshot", "build": { "...": "..." }, "agents": [ ], "tasks": [ ] }
{ "kind": "ping", "ts": "2026-11-06T14:21:30Z" }
{ "kind": "end", "reason": "build_completed" }
```

- On connect without `since_seq`, the server sends one `snapshot` message with the current build, agents and tasks, followed by live events.
- With `since_seq`, the server skips the snapshot and replays events from that sequence number.
- The server sends `ping` every 15 seconds. Clients reconnect with the last seen `seq` after a drop.
- Messages are ordered by `seq`. The client must apply them in order and ignore any `seq` it has already processed.

Client to server messages:

```json
{ "kind": "pause_replay" }
{ "kind": "resume_replay" }
{ "kind": "seek", "seq": 500 }
{ "kind": "set_speed", "speed": 2 }
```

Replay controls apply only when `replay=true`.

### 8.2 Experiment stream

`WS /api/v1/experiments/{experiment_id}/stream` sends `run_started`, `run_completed` (with `metrics`) and `experiment_completed` messages, so the evaluation dashboard updates live.

---

## 9. Agent action contract (Qwen 3.5 JSON output)

Agents return structured JSON so the runtime can execute tool calls reliably (section 11 of the overview). The runtime validates every response against this schema and retries once with the validation error before reporting `422 MODEL_OUTPUT_INVALID`.

```json
{
  "thought": "The hero section needs design tokens first, but they exist, so I can build it.",
  "action": {
    "tool": "write_file",
    "args": {
      "path": "src/pages/index.html",
      "content": "<!doctype html>...",
      "base_version": 2
    }
  },
  "signals": [
    { "type": "needs_review", "target": "section:hero", "strength": 0.6 }
  ]
}
```

**Allowed tools**

| Tool | Args | Maps to |
| --- | --- | --- |
| `read_blackboard` | `zones` (list), `filters` | GET tasks, signals, artifacts, scores |
| `place_bid` | `task_id` | POST bids |
| `claim_task` | `task_id` | POST claim |
| `create_task` | task fields | POST tasks |
| `write_file` | `path`, `content`, `base_version` | PUT artifacts |
| `emit_signal` | `type`, `target`, `message`, `strength` | POST signals |
| `resolve_signal` | `signal_id` | POST resolve |
| `post_proposal` | `topic`, `summary`, `content` | POST proposals |
| `cast_vote` | `proposal_id`, `value`, `critique` | POST votes |
| `run_build` | none | Sandbox build command |
| `run_tests` | `suite` | Playwright, Lighthouse |
| `take_screenshot` | `viewport` | Playwright screenshot |
| `compare_visual` | `iteration` | Vision comparison plus SSIM |
| `submit_task` | `result_summary`, `requires_review` | POST submit |
| `idle` | none | No action this turn |

The `thought` field is stored in `agents.memory` and is shown when the user clicks a cursor. It is not placed in the event payload.

---

## 10. Constraints and non-functional notes

| Topic | Requirement |
| --- | --- |
| Concurrency | A single shared model on one GPU. The runtime queues model calls. API writes must be safe under concurrent agents (transactions, conditional updates) |
| Performance | `GET` endpoints respond in under 200 ms for builds with up to 500 tasks and 10,000 events. WebSocket event delivery latency under 300 ms from write to client |
| Reliability | One agent failure must not stop the build (lease expiry and recovery) |
| Reproducibility | `builds.seed`, `config.models` and the saved `prompt` are stored. Model versions and digests are recorded in the first `build_started` event payload |
| Security | Sandbox path validation on every file write. No network access for generated code. Preview served with a restrictive CSP. Upload limits: images up to 10 MB |
| Data retention | Events and scores are kept indefinitely for benchmarks. Sandboxes can be deleted after export |
| Observability | Every decision, action and score is an event. Exports are NDJSON and CSV |

---

## 11. Traceability

| Use case or requirement | Data model | API |
| --- | --- | --- |
| UC1 Prompt build, FR1 | `builds`, `tasks`, `events` | `POST /builds`, WS stream |
| UC2 Screenshot build, FR1, FR6 | `reference_images`, `scores` | `POST /builds` (multipart), `GET /scores/visual-history` |
| UC3 Inspect agent | `agents`, `events` | `GET /agents/{id}` |
| UC4 Rebuild, FR10 | `builds.parent_build_id` | `POST /builds/{id}/rebuild` |
| UC5 Benchmark, FR12 | `experiments`, `experiment_runs` | `/experiments/*` |
| UC6 Failure injection, FR11 | `agents`, `events` | `POST .../inject-failure` |
| FR2 Seed tasks | `tasks` | `POST /tasks` with `created_by_agent_id = null` |
| FR3 Bidding and leases | `tasks`, `bids` | bids, claim, heartbeat |
| FR4 Artifacts and signals | `artifacts`, `artifact_versions`, `signals` | `/artifacts`, `/signals` |
| FR5 Build and preview | `artifacts`, sandbox | `/preview/*` |
| FR7 Bug and fix tasks | `signals`, `tasks` | signals, tasks |
| FR8, FR9 Events and cursors | `events` | `/events`, WS stream |
| O7, RQ3 Resilience | `tasks.lease_expires_at`, `events` | reaper behavior (5.3), `inject-failure` |

---

## 12. Open items for mentor review

1. Confirm the default lease length (90 s) and bid window (500 ms) against actual Qwen 3.5 latency on the RTX 4050 laptop.
2. Decide whether bids are persisted (4.9) or kept in memory only.
3. Decide the visual similarity metric for the main results (`ssim` or `phash`), and whether to report both.
4. Confirm exact Qwen 3.5 model names and quantized builds on Ollama or Hugging Face before fixing `config.models`.
5. Decide whether PostgreSQL is needed, or SQLite with WAL mode is enough for the expected write rate.
