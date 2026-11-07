# System Architecture and Design Document

# Swarm Website Builder

*Decentralized multi-agent website generation powered by Qwen 3.5*

| Field | Value |
| --- | --- |
| Prepared by | [Your name] |
| Document | System Architecture and Design Document |
| Version | 1.0 |
| Date | November 2026 |
| Status | Draft for mentor review |
| Companion documents | Project document v1.0, PRD v1.0, TRD v1.0, SRS v1.0 |

---

## 1. Introduction

### 1.1 Purpose

This document describes the architecture and detailed design of the Swarm Website Builder: its structure, components, interactions, coordination algorithms and key design decisions. It explains how the requirements in the PRD, TRD and SRS are satisfied.

### 1.2 Design drivers

| Driver | Consequence for the design |
| --- | --- |
| No central controller (O3) | Coordination only through a shared blackboard; no component assigns tasks |
| Qwen 3.5 in every agent (O4) | One uniform agent runtime where every decision is a Qwen call |
| Real-activity visualization (O5) | Append-only event log as the single source of truth; UI only replays events |
| Resilience (O7) | Leases and heartbeats return work from failed agents to the pool |
| Small laptop GPU (NFR6) | One shared quantized model, a request queue, no heavy Docker |
| Reproducible research (NFR4) | Seeds, saved prompts, saved model versions, stored config per build |

### 1.3 Architectural style

- **Blackboard architecture** for coordination (agents are independent knowledge sources that read and write a shared store).
- **Stigmergy:** agents influence each other indirectly through marks (tasks, signals, artifacts).
- **Event sourcing for observability:** all agent actions are recorded as ordered events that drive the UI, replay and evaluation.
- **Layered system** around the swarm runtime: interface, API, runtime, model, sandbox, storage.

## 2. Architectural overview

### 2.1 Layers

| # | Layer | Technology | Responsibility |
| --- | --- | --- | --- |
| 1 | Interface | React, JavaScript, CSS, SVG | Input, cursors, task board, log, preview, dashboard |
| 2 | API | FastAPI, REST and WebSocket | Build control, event streaming, preview serving, benchmark and failure-injection endpoints |
| 3 | Swarm runtime | Python, asyncio | Blackboard, agent runner, bidding, leases, signal decay, event log |
| 4 | Model | Qwen 3.5 via Ollama or llama.cpp; optional Qwen3.5-Plus | Reasoning, code, vision, structured output, critique |
| 5 | Execution sandbox | Temporary project folder | Write, build and test generated code |
| 6 | Storage | SQLite or PostgreSQL | Blackboard state, events, results |

### 2.2 Context diagram

```
        +-----------+            +----------------------+
        |   User    |            |  Researcher          |
        | (builder) |            |  (benchmarks, kills) |
        +-----+-----+            +----------+-----------+
              |                             |
              v                             v
      +-----------------------------------------------+
      |           Swarm Website Builder               |
      +--------+----------------------+---------------+
               |                      |
               v                      v
      +----------------+     +-------------------+
      | Local Qwen 3.5 |     | Hosted Qwen3.5-   |
      | (Ollama/llama  |     | Plus (optional)   |
      |  .cpp)         |     +-------------------+
      +----------------+
```

### 2.3 Container diagram

```
+------------------------------------------------------------------+
| Browser: React app                                               |
|  PromptPanel | CursorOverlay | TaskBoard | LogStream | Preview   |
|  AgentList | ReplayControls | EvalDashboard                      |
+----------------+---------------------------+---------------------+
                 | REST                      | WebSocket
+----------------v---------------------------v---------------------+
| FastAPI service                                                  |
|  BuildRouter | EventStreamer | PreviewServer | BenchmarkRouter   |
|  FailureInjectionRouter                                          |
+----------------+-------------------------------------------------+
                 | in-process calls / async queues
+----------------v-------------------------------------------------+
| Swarm runtime (asyncio)                                          |
|  +-----------+  +------------+  +------------+  +-------------+  |
|  | Blackboard|  | Agent      |  | Lease      |  | Signal      |  |
|  | service   |  | runner     |  | manager    |  | decay worker|  |
|  +-----+-----+  +-----+------+  +------+-----+  +------+------+  |
|        |              |                |               |         |
|  +-----v--------------v----------------v---------------v------+  |
|  | Event log writer (append-only)                             |  |
|  +------------------------------------------------------------+  |
|  +-------------------+   +-------------------+                   |
|  | Model gateway     |   | Tool executor     |                   |
|  | (queue, routing)  |   | (sandbox tools)   |                   |
|  +---------+---------+   +---------+---------+                   |
+------------|-----------------------|-----------------------------+
             v                       v
   +-------------------+    +--------------------------+
   | Ollama / llama.cpp|    | Sandbox folder           |
   | Qwen 3.5 (4-bit)  |    | build, Playwright,       |
   +-------------------+    | Lighthouse               |
                            +--------------------------+
        Storage: SQLite / PostgreSQL (blackboard, events, results)
```

## 3. Component design

### 3.1 Blackboard service

**Responsibility:** the only shared state between agents. Provides transactional read and write access to five zones.

| Zone | Content | Key operations |
| --- | --- | --- |
| Goal | User request, reference image | `get_goal` |
| Tasks | Work units with status, owner, lease, dependencies, priority | `create_task`, `list_open`, `claim_task`, `renew_lease`, `update_status`, `release_task` |
| Artifacts | Versioned files and specs | `read_artifact`, `write_artifact(base_version)`, `list_versions` |
| Signals | Decaying messages | `emit_signal`, `list_signals(min_strength)` |
| Scores | Test and similarity results | `write_score`, `read_scores` |

**Design rules**

- Every mutating operation runs in a database transaction and emits an event.
- `claim_task` is a compare-and-set: it succeeds only if the task is `open` and all dependencies are `done`.
- `write_artifact` succeeds only if `base_version` equals the current version (optimistic locking).
- Agents see the blackboard only through this service, never through each other.

### 3.2 Agent runner

**Responsibility:** hosts N agents as asyncio tasks and gives each its role configuration, memory and tools. The runner does not choose tasks and has no scheduling authority; it only starts, stops and supervises agent loops.

Role configuration:

| Field | Meaning |
| --- | --- |
| `role` | UI/UX, Frontend, Backend, Database, Testing, Integration, Reviewer |
| `system_prompt` | Role instructions and output schema |
| `tools` | Allowed tool subset |
| `model_tier` | 0.8B–2B, 4B, 9B or hosted |
| `bid_profile` | Role-match weights per task type |
| `limits` | Max actions per task, max retries |

### 3.3 Agent internal design

Each agent has:

- **Perception:** a filtered view of the blackboard (open tasks it may bid on, strong signals, artifacts relevant to its current task).
- **Working memory:** current task, recent actions and observations (bounded by a context budget).
- **Decision module:** a Qwen call that returns a JSON action.
- **Action executor:** validates the action, calls a tool, writes results to the blackboard.
- **Heartbeat:** renews the lease on the current task.

#### Agent loop

```
loop:
  observe  -> read tasks, signals, artifacts
  if no current task:
      bids = [bid(task) for open tasks]
      claim highest bid (atomic)           -> event task_claimed
  decide   -> Qwen returns JSON action
  validate -> schema, path, tool allowed
  act      -> tool executes (write file, build, test, screenshot)
  report   -> write artifact / signal / score, log events
  heartbeat -> renew lease
until: no open tasks and completion criteria met, or stop requested
```

#### Agent state machine

```
 spawned -> idle -> bidding -> working -> reporting -> idle
                       |           |
                       |           +--(error / kill)--> failed
                       +--(no tasks)--> idle
 paused <-> any state (failure injection)
```

### 3.4 Bidding and lease manager

**Bid computation** (per idle agent, per open task):

```
bid = w1 * role_match(task, agent)
    + w2 * (1 - load(agent))
    + w3 * past_success(agent, task_type)
    + w4 * priority(task)
    + w5 * signal_boost(task)      # strong related signals raise the bid
```

- Weights are configuration, stored with each run.
- Tie-break: lower agent id, a fixed and logged rule.
- A rejected claim (task already taken) causes the agent to re-observe and re-bid.

**Lease lifecycle**

```
claim -> lease(expiry = now + T)
  heartbeat every H seconds  -> expiry extended
  no heartbeat before expiry -> lease_manager sets task 'open', clears owner,
                                increments retries, logs agent_failed
```

The lease manager is a passive timer that enforces expiry. It never assigns work, so it does not act as a controller.

### 3.5 Signal decay worker

- Signals hold `strength` and `last_reinforced`.
- Effective strength is computed as `strength * 0.5^((now - last_reinforced) / half_life)`.
- Re-emitting the same signal for the same target adds to strength (capped).
- Signals below a minimum are pruned.
- Agents read effective strength, so priorities shift without any central decision.

### 3.6 Model gateway

**Responsibility:** the single path from agents to Qwen.

| Function | Detail |
| --- | --- |
| Routing | Maps each agent or step to a model tier |
| Queueing | A bounded request queue sized to GPU capacity, with a few concurrent requests at most |
| Vision | Accepts images for screenshot reading and comparison |
| Structured output | Requests JSON and returns it for validation |
| Fallback | Optional escalation to Qwen3.5-Plus for designated hard steps; system works without it |
| Recording | Logs model name, version, parameters, tokens and latency per call |

### 3.7 Tool executor and sandbox

**Tools exposed to agents**

| Tool | Description |
| --- | --- |
| `read_file`, `write_file` | Sandbox-confined file access |
| `run_build` | Build the site |
| `run_tests` | Playwright functional tests |
| `take_screenshot` | Playwright screenshot of a page or section |
| `visual_diff` | Compute SSIM or perceptual-hash similarity to the reference |
| `run_lighthouse` | Performance, accessibility and best-practices scores |
| `bb_*` | Blackboard operations |

**Safety design**

- All paths are normalized and must stay inside the build folder; symlinks are not followed outside it.
- Build and test steps run without access to personal files; network is disabled or restricted.
- The sandbox folder is deleted after the build unless kept.
- Docker is an option only if resources allow.

### 3.8 Event log writer

- One writer serializes all events with a monotonically increasing sequence number.
- Events are appended in the same transaction as the state change that caused them, so the log and the blackboard never disagree.
- The writer publishes each event to the WebSocket streamer.

### 3.9 API layer

| Component | Role |
| --- | --- |
| BuildRouter | Start build, rebuild, get status |
| EventStreamer | WebSocket stream and stored-event replay |
| PreviewServer | Serves the generated site from the sandbox for the iframe preview |
| AgentRouter | Agent detail, kill and pause |
| BenchmarkRouter | Run experiment configurations, fetch results |

### 3.10 Interface components

| Component | Function |
| --- | --- |
| PromptPanel | Text prompt and screenshot upload, start button |
| PreviewPane | Iframe of the generated site |
| CursorOverlay | Animated cursors positioned over preview sections from events |
| TaskBoard | Columns by task status |
| AgentList | Role, status and current task per agent |
| LogStream | Scrolling event log |
| ProgressBar | Share of tasks done and score progress |
| ReplayControls | Play, pause, seek, speed |
| ControlsPanel | Rebuild, kill, pause |
| EvalDashboard | Benchmark tables and charts |

## 4. Key workflows

### 4.1 Prompt-to-website build

```
User        API        Runtime/Blackboard      Agents                Qwen
 |  prompt   |               |                    |                    |
 |---------->| POST /builds  |                    |                    |
 |           |-------------->| write Goal         |                    |
 |           |               | spawn agents       |                    |
 |           |               |------------------->| seeding agent      |
 |           |               |                    |-- decompose goal ->|
 |           |               |<-- create tasks ---|<-- JSON tasks -----|
 |           |               |                    |                    |
 |           |               | agents bid & claim (atomic)             |
 |           |               |<------------------>| decide/act loops ->|
 |           |               | artifacts, signals, events              |
 |<== WebSocket events (cursors, log, preview) ==================      |
 |           |               | Testing agent: build, test, screenshot  |
 |           |               |<-- bug/fix tasks --|                    |
 |           |               | ... until completion criteria ...       |
 |<-- status: done ----------|                    |                    |
```

### 4.2 Screenshot-to-website with vision loop

1. The user uploads a screenshot; it is stored in the Goal zone.
2. UI/UX agent uses Qwen vision to write a design spec (layout, colors, typography, section list).
3. Frontend agents claim section tasks and produce code.
4. The Testing agent renders the site, takes screenshots and computes similarity to the reference.
5. If similarity is below threshold, the Testing agent asks Qwen vision to describe the differences, then posts visual-difference tasks per section.
6. Agents claim and fix those tasks; the loop repeats until the threshold or the iteration limit is reached.

```
render -> screenshot -> compare (score) -> below threshold?
   ^                                          | yes
   |                                          v
   +---- fix tasks <---- difference tasks <---+
                         (iteration += 1; stop at limit)
```

### 4.3 Failure and recovery

```
t0  Frontend-2 holds task T7 (lease expires at t0+T)
t1  Researcher kills Frontend-2          -> event agent_failed
t2  heartbeats stop
t3  lease expires: T7 -> open, retries+1 -> event task released
t4  Frontend-1 observes open T7, bids, claims -> event agent_recovered
t5  T7 completes -> event task_done
```

Recovery time = `t4 - t1` and is recorded for experiment E3.

### 4.4 Conflict resolution

1. Agent A and Agent B both read file `styles.css` at version 3.
2. A writes with `base_version=3` and succeeds, creating version 4.
3. B writes with `base_version=3`; the write is rejected as stale.
4. B re-reads version 4 and retries; if the edits overlap, B emits `needs_merge`.
5. The Integration agent claims the conflict task, merges both changes and writes version 5.

### 4.5 Collective design decision

1. A `design_choice_needed` signal appears (for example navigation layout).
2. Two or more agents post proposals as artifacts.
3. Reviewer agents critique each proposal and cast votes as signals.
4. The proposal with the highest vote total is selected; the Integration agent may merge useful parts of losing proposals.
5. The outcome is written as a design spec artifact and logged.

### 4.6 Rebuild

The user submits a modified prompt. A new build is created, linked to the original by id; the original's events remain unchanged.

## 5. Data design

### 5.1 Entity-relationship overview

```
build 1---* agent
build 1---* task        task *---* task (dependencies)
build 1---* artifact    artifact 1---* artifact_version
build 1---* signal
build 1---* score
build 1---* event       agent 1---* event
agent 1---* model_call
experiment 1---* experiment_run   experiment_run *---1 build
```

### 5.2 Main tables (summary)

| Table | Key columns |
| --- | --- |
| `build` | id, parent_build_id, mode, prompt, reference_image_path, config_json, seed, status, created_at, finished_at |
| `agent` | id, build_id, role, model_tier, status, last_heartbeat |
| `task` | id, build_id, title, description, type, status, owner_agent_id, lease_expiry, priority, retries, target_section |
| `task_dependency` | task_id, depends_on_task_id |
| `artifact_version` | artifact_id, version, path, author_agent_id, content_hash, created_at |
| `signal` | id, build_id, type, target, strength, last_reinforced, emitters_json |
| `score` | id, build_id, type, value, iteration, created_at |
| `event` | seq, build_id, timestamp, agent_id, type, target, payload_json |
| `model_call` | id, agent_id, model, version, tokens_in, tokens_out, latency_ms, params_json |
| `experiment_run` | id, experiment_id, system, prompt_id, repetition, seed, metrics_json |

Full schemas and indexes belong in the data model and API specification.

### 5.3 Consistency rules

- Task claim, artifact write and signal update are single transactions.
- Events are inserted in the same transaction as the change they describe.
- Event `seq` is strictly increasing per build, which guarantees replay order.

## 6. Visualization design

### 6.1 Principle

The event log is the single source of truth. The interface only replays events, so a cursor moves only when its agent does something real.

### 6.2 Event to cursor mapping

| Event | Cursor behavior |
| --- | --- |
| `agent_spawned` | Cursor appears with the role color |
| `task_claimed` | Cursor moves to the page section the task targets |
| `file_edit` | Typing or highlight on that section |
| `signal_emitted` | Short pulse or trail at the target |
| `test_run` | Cursor moves to the test panel or preview |
| `test_failed` | Target section flashes red |
| `fix_applied` | Target section flashes green |
| `agent_failed` | Cursor fades out and a failure marker is shown |
| `agent_recovered` | Replacement cursor takes over the task |
| `task_done` | Section marked complete and progress updates |

### 6.3 Rendering design

- The generated site is shown in an iframe; each section carries a stable attribute such as `data-section="hero"`.
- The overlay layer reads section bounding boxes from the iframe and positions SVG or DOM cursors above them.
- Cursor motion is animated with CSS transitions between section positions; effects (pulse, flash) are triggered per event.
- Cursors carry a role color and a label, and failure and success states also use an icon so they do not depend on color alone.
- A client-side event queue orders events by `seq` and plays them with their timestamps, enabling live mode and replay at 1x or faster.

### 6.4 Live vs replay

| Mode | Source | Timing |
| --- | --- | --- |
| Live | WebSocket | As events arrive |
| Replay | Stored events via REST | Original timestamps, adjustable speed, seek by `seq` |

### 6.5 Handling serialized GPU work

Because the GPU runs model calls one at a time or a few at a time, true parallelism is limited. The interface still shows several agents active because it renders from event timestamps (claims, edits, signals and heartbeats), not from GPU concurrency.

### 6.6 Agent detail panel

Clicking a cursor opens a panel with the agent's role, model tier, current task, recent actions (from its events) and current signals it reacts to.

## 7. Evaluation architecture

### 7.1 System variants

| ID | System | Architecture |
| --- | --- | --- |
| B1 | Single agent, one-shot | One Qwen call generates the whole site |
| B2 | Single agent with test-and-fix | One agent, same Testing tools, same loop limits |
| B3 | Centralized pipeline | An orchestrator assigns tasks to labeled agents in a fixed order |
| S | Swarm | The architecture in this document |

All variants share the model gateway, sandbox, testing tools and metrics code, so differences come from the coordination architecture.

### 7.2 Benchmark harness

```
experiment config (system, prompt set, repetitions, seeds, failure plan)
        |
        v
for each (system, prompt, repetition):
    create build with fixed seed -> run -> collect metrics
        |
        v
experiment_run rows -> aggregation (mean, variation) -> dashboard + CSV/JSON
```

### 7.3 Failure injection

The harness can schedule a kill or pause at a given build progress point (for example 50% of tasks done). The kill goes through the same agent control interface as the manual button.

## 8. Resource and deployment design

### 8.1 Target machine

Intel i5 laptop, RTX 4050 laptop GPU (typically 6 GB VRAM; verify), about 256 GB storage with part used.

### 8.2 Model memory strategy

| Decision | Reason |
| --- | --- |
| 4-bit quantized models | Fit in limited VRAM |
| One loaded model instance shared by agents via role prompts | Avoid loading several models |
| 9B used only for single hard decisions, one at a time | Memory limit |
| Two or three model files on disk | Storage limit |
| Fine-tuning and large benchmarks on Colab or Kaggle | Local GPU too small |

### 8.3 Deployment view

```
Developer laptop
 ├─ Ollama / llama.cpp  (Qwen 3.5, 4-bit)
 ├─ Python process: FastAPI + swarm runtime (asyncio)
 ├─ SQLite file
 ├─ Temp sandbox folders (per build)
 └─ Node dev server: React interface (browser at localhost)
```

## 9. Cross-cutting design

### 9.1 Reliability

| Mechanism | Purpose |
| --- | --- |
| Lease and heartbeat | Recover tasks from failed or stalled agents |
| Retry limit per task | Stop repeated failure loops |
| Iteration limit | Bound fix and refinement cycles |
| Global time budget | End builds that do not converge, with a status listing unfinished work |
| Transactional state | No partial updates after a crash |

### 9.2 Security

| Mechanism | Purpose |
| --- | --- |
| Path normalization and confinement | Stop sandbox escape |
| Tool allowlist per role | Limit what agents can do |
| Action schema validation | Reject malformed or unknown actions |
| Restricted network | Limit damage from generated code |
| Secrets outside repository | Protect hosted API key |
| Upload validation | Check image type and size |

### 9.3 Observability

All decisions, actions, scores and model calls are logged. A build can be reconstructed and replayed from its event log.

### 9.4 Reproducibility

Each build stores seed, prompt, config (bid weights, decay, lease timeout), model names and versions. Experiment runs reference these records.

### 9.5 Error handling

| Situation | Behavior |
| --- | --- |
| Invalid JSON from Qwen | Bounded retry with an error hint, then release the task |
| Tool error (build fails) | Convert into a `bug_found` signal and a fix task |
| Model queue overload | Back-pressure: agents wait, no dropped events |
| Agent exception | Mark agent failed, lease expires, task reopens |
| Stale artifact write | Reject, agent re-reads and retries |

## 10. Key design decisions

| ID | Decision | Alternatives considered | Rationale |
| --- | --- | --- | --- |
| D1 | Blackboard with stigmergy for coordination | Message passing between agents; central orchestrator | Matches the swarm goal, no controller, easy to log and visualize |
| D2 | Bidding with leases for task allocation | Round-robin, random claiming, central assignment | Allows role specialization, self-healing, and no authority |
| D3 | One shared quantized model with role prompts | One model per agent | Fits the 6 GB GPU |
| D4 | Event log as the single source of truth for UI | UI reading state directly | Guarantees cursors reflect real activity and enables replay |
| D5 | Optimistic versioning for artifacts | Locks on files | Avoids deadlocks; conflicts become Integration tasks |
| D6 | Temp-folder sandbox before Docker | Docker by default | Lower resource use on the laptop |
| D7 | JSON action contract validated by the runtime | Free-text actions | Reliable tool execution with small models |
| D8 | Passive lease manager | Active supervisor assigning replacements | Keeps the system free of any controller |
| D9 | Signals with decay and reinforcement | Permanent flags | Priorities adapt without a central decision |
| D10 | Same tools and gateway for all baselines | Separate baseline implementations | Fair comparison, differences come from architecture |

## 11. Design risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Small models produce weak code or invalid JSON | Schema validation, retries, 4B/9B for hard roles, test-and-fix loops |
| Poor bid weights or signal parameters | Configurable parameters, pilot tuning, log analysis |
| GPU becomes the bottleneck | Request queue, short prompts, limited agent count |
| Cursor positions do not match preview | Stable section ids and a single event source |
| Merge conflicts frequent | Section-level task granularity so agents touch different files |
| Lease timeout too short or long | Tune on measured model latency; heartbeat independent of model call duration |

A note on the last row: the heartbeat should run as its own async task, separate from the model call, so a slow Qwen response does not look like a crashed agent.

## 12. Requirements traceability

| Design element | Requirements addressed |
| --- | --- |
| Blackboard service (3.1) | REQ-2.x, 3.x, 4.x; O3 |
| Agent runner and loop (3.2, 3.3) | REQ-5.x; O4 |
| Bidding and lease manager (3.4) | REQ-3.x, 12.x; O3, O7 |
| Signal decay (3.5) | REQ-4.5 to 4.9 |
| Model gateway (3.6) | REQ-5.2, 5.9, 5.10, 9.5; NFR-1.4 |
| Tool executor and sandbox (3.7) | REQ-6.x, 7.x; NFR-5.x |
| Event log writer (3.8) | REQ-9.x; NFR-3.x |
| Visualization (6) | REQ-10.x; O5 |
| Evaluation architecture (7) | REQ-13.x; O6 |
| Resource design (8) | NFR-6.x, CR-2, CR-3 |

## 13. Open design questions

1. Exact context budget per agent and how much blackboard history to include in each Qwen call.
2. Whether Reviewer agents run continuously or only when a `needs_review` signal is strong.
3. Granularity of tasks (per page, per section or per component) that best limits conflicts.
4. Whether the vision loop compares full pages or per-section crops.
5. SQLite concurrency behavior under the expected agent count; fallback to PostgreSQL if needed.
6. Default values for lease timeout, heartbeat interval, signal half-life and bid weights.

## 14. Glossary

- **Blackboard:** shared memory that agents read and write to coordinate.
- **Stigmergy:** indirect coordination through marks left in a shared environment.
- **Lease:** a time-limited claim on a task that expires if the agent stalls.
- **Heartbeat:** periodic signal from an agent that renews its lease.
- **Signal:** a short blackboard message whose strength decays and can be reinforced.
- **Event log:** append-only record of every agent action, used for visualization and analysis.
- **Optimistic versioning:** writes name the version they are based on and are rejected if stale.
- **Quantization:** compressing a model to use less memory, for example 4-bit.
