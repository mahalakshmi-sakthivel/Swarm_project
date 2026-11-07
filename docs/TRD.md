# Technical Requirements Document (TRD)

# Swarm Website Builder

*Decentralized multi-agent website generation powered by Qwen 3.5*

| Field | Value |
| --- | --- |
| Prepared by | [Your name] |
| Document | Technical Requirements Document |
| Version | 1.0 |
| Date | November 2026 |
| Status | Draft for mentor review |
| Companion documents | Project document v1.0, PRD v1.0 |

---

## 1. Purpose and scope

This TRD defines **how** the Swarm Website Builder is built: architecture, components, coordination mechanisms, model usage, technology stack, resource limits and technical quality targets. It implements the requirements in the PRD (FR1–FR12, NFR1–NFR7) and the objectives O1–O7.

Detailed schemas and endpoint contracts will be specified in the data model and API specification. Numbered testable requirements will be in the SRS.

## 2. Technical goals

| ID | Technical goal | Traces to |
| --- | --- | --- |
| TG1 | No component assigns tasks to agents; all coordination goes through the blackboard. | O3 |
| TG2 | Every agent decision is produced by a Qwen 3.5 call. | O4 |
| TG3 | The event log is the single source of truth for visualization, replay and evaluation. | O5, O6 |
| TG4 | Failed or stalled work returns to the task pool automatically. | O7 |
| TG5 | The whole system runs on a laptop with a 6 GB GPU using quantized models. | NFR6 |
| TG6 | Experiments are reproducible. | NFR4 |

## 3. System architecture

### 3.1 Layers

| # | Layer | Technology | Responsibility |
| --- | --- | --- | --- |
| 1 | Interface | React, JavaScript, CSS, SVG | Prompt and screenshot input, cursor visualization, task board, log stream, live preview, evaluation dashboard |
| 2 | API | FastAPI (REST + WebSocket) | Start builds, stream events, serve previews, expose benchmark and failure-injection controls |
| 3 | Swarm runtime | Python, asyncio | Blackboard, agent runner, bidding and lease logic, signal decay, event log |
| 4 | Model | Qwen 3.5 via Ollama or llama.cpp; optional Qwen3.5-Plus (hosted API) | Reasoning, code generation, vision, structured output, critique |
| 5 | Execution sandbox | Temporary project folder; Docker only if resources allow | Write, build and test generated code in isolation |
| 6 | Storage | SQLite (development), PostgreSQL (optional) | Blackboard state, event log, evaluation results |

### 3.2 Component diagram

```
+--------------------------------------------------------------+
|  Interface (React)                                           |
|  prompt/screenshot input | cursors | task board | preview    |
+-------------------+------------------------+-----------------+
                    | REST                   | WebSocket (events)
+-------------------v------------------------v-----------------+
|  API layer (FastAPI)                                         |
+-------------------+------------------------------------------+
                    |
+-------------------v------------------------------------------+
|  Swarm runtime (asyncio)                                     |
|  +-------------+   +--------------+   +-------------------+  |
|  | Agent runner|<->|  Blackboard  |<->|  Event log        |  |
|  | (N agents)  |   | tasks/signals|   |  (append-only)    |  |
|  +------+------+   | artifacts    |   +-------------------+  |
|         |          +--------------+                          |
+---------+--------------------------------------------------+-+
          |                                                  |
+---------v-----------+   +------------------+   +-----------v--+
| Model layer         |   | Execution sandbox|   | Storage      |
| Qwen 3.5 (Ollama /  |   | temp folder:     |   | SQLite /     |
| llama.cpp)          |   | write/build/test |   | PostgreSQL   |
+---------------------+   +------------------+   +--------------+
```

### 3.3 High-level data flow

1. The user submits a prompt or screenshot; the goal is written to the blackboard.
2. A seeding step, performed by an ordinary agent using Qwen, splits the goal into initial tasks. This is a one-time action and gives that agent no authority afterwards.
3. Agents read the blackboard, bid for tasks matching their role, and claim them.
4. Agents write artifacts (files, designs, API routes) and signals back to the blackboard.
5. Every action is appended to the event log.
6. The Testing agent builds the site, runs tests, takes screenshots and posts bug and visual-difference tasks.
7. The loop repeats until the completion criteria are met.
8. The event log streams to the interface, which animates cursors and updates the preview.

## 4. Swarm runtime design

### 4.1 Blackboard zones

| Zone | Content |
| --- | --- |
| Goal | User request and reference image |
| Tasks | Units of work with status, owner, dependencies and priority |
| Artifacts | Versioned files and specs produced by agents |
| Signals | Short messages influencing other agents (e.g. `need_styling`, `bug_found`, `needs_review`, `blocked`) |
| Scores | Test results and visual similarity values |

### 4.2 Agent loop

Each agent runs this loop independently:

1. **Observe:** read new tasks, signals and artifacts.
2. **Decide:** ask Qwen what to do next, or bid on a task.
3. **Act:** call tools (write file, run build, take screenshot, run test).
4. **Report:** write results and signals to the blackboard and log events.
5. **Repeat** until no open tasks remain and completion criteria pass.

### 4.3 Task lifecycle

```
open -> claimed -> in_progress -> in_review -> done
  ^         |            |
  |         v            v
  +------ expired / failed (lease timeout or error)
```

A failed or expired task returns to `open`.

### 4.4 Task allocation by bidding

- Each idle agent computes a bid for each open task from **role match**, **current load** and **past success on similar tasks**.
- The highest bid wins. Claims are **atomic** (single database transaction or compare-and-set), so two agents can never hold the same task.
- A claim is a **lease with a timeout**. The lease is renewed by agent heartbeats; if the agent crashes or stalls, the lease expires and the task becomes `open`. This is the self-healing mechanism (TG4).

Suggested bid function (tunable, to be validated experimentally):

```
bid = w1 * role_match + w2 * (1 - load) + w3 * past_success + w4 * task_priority
```

### 4.5 Signals with decay

- Each signal has a strength that decays over time (for example exponential decay with a configurable half-life).
- Repeated emission of the same signal by several agents reinforces its strength.
- Agents give priority to strong signals, imitating pheromone trails.
- Signals below a minimum strength are pruned.

### 4.6 Conflict handling

- Artifacts use **optimistic versioning**: each write names the version it is based on.
- If a write is based on a stale version, it is rejected and the agent must re-read.
- The Integration agent merges concurrent changes or posts a conflict task.

### 4.7 Collective decisions

For design choices, several agents post proposals, Reviewer agents critique them, and a vote selects the winner. Good parts of losing proposals can be merged by the Integration agent.

### 4.8 Termination and safety limits

| Mechanism | Purpose |
| --- | --- |
| Completion criteria | Site builds, all tests pass, no strong bug signals remain, and (screenshot mode) visual similarity above threshold or iteration limit reached |
| Iteration limit | Cap on fix and refinement cycles per task and per build |
| Task retry limit | Prevents a task failing and reopening forever |
| Global time budget | Stops a build that does not converge |

## 5. Agent roles

Every agent is Qwen 3.5 with a role-specific system prompt, memory and tools. No agent has authority over others.

| Agent | Reads | Writes | Main tools |
| --- | --- | --- | --- |
| UI/UX | Goal, reference image | Design spec, style signals | Vision, write spec |
| Frontend | Design spec, tasks | HTML, CSS, JS or React files | Write file, run build |
| Backend | Tasks, data schema | FastAPI routes | Write file, run server |
| Database | Tasks, API needs | Schema and seed data | Write file, run SQL |
| Testing | Artifacts | Bug signals, fix tasks, scores | Build, Playwright, Lighthouse, screenshot, visual diff |
| Integration | Artifacts, conflicts | Integrated project | Read/merge files |
| Reviewer | Artifacts, proposals | Review signals, votes | Read artifacts |

A small build can run with three to four roles. Roles are configuration (prompt + tool set + bid profile), so they can be added or removed without changing the runtime.

## 6. Qwen 3.5 integration

### 6.1 Uses of Qwen inside each agent

| Use | Detail |
| --- | --- |
| Reasoning and decisions | Choosing tasks, planning steps, deciding when to ask for help |
| Code generation | HTML, CSS, JavaScript, React, Python, SQL |
| Vision | Reading a reference screenshot and comparing it with the generated page (Qwen 3.5 is natively multimodal) |
| Structured output | Actions returned as JSON for reliable tool execution |
| Critique | Reviewing other agents' output and voting |

### 6.2 Structured action contract

Agents return actions as JSON validated by the runtime before execution. Illustrative shape:

```json
{
  "action": "write_file",
  "task_id": "t-042",
  "args": { "path": "src/components/Hero.jsx", "content": "..." },
  "signals": [{ "type": "needs_review", "target": "Hero" }],
  "reasoning_summary": "Implemented hero section per design spec v3"
}
```

Requirements:

- Invalid or unparseable JSON triggers a bounded retry with an error message, then the task is released.
- Unknown actions or paths outside the sandbox are rejected and logged.
- Only validated actions can change blackboard or sandbox state.

### 6.3 Model sizing strategy

Exact availability and quantized versions must be verified on Hugging Face or Ollama before download.

| Use | Model | Where it runs |
| --- | --- | --- |
| Simple agents (linting, styling, formatting) | 0.8B to 2B | Local GPU |
| Main agents (frontend, backend, testing) | 4B | Local GPU |
| Hard single decisions (optional) | 9B | Local GPU, one at a time |
| Hardest steps (optional) | Qwen3.5-Plus | Hosted API |

### 6.4 Model serving

- Serve through Ollama or llama.cpp with 4-bit quantized models.
- Load **one model instance** and share it across agents through role prompts.
- The runtime routes each call to the model tier assigned to that agent or step.
- Concurrency is limited by a request queue sized to GPU capacity; agents take turns when needed.
- Every call records model name and version, prompt, parameters, token counts and latency for reproducibility (NFR4).

### 6.5 Optional fine-tuning

Fine-tune one small Qwen 3.5 model for a single role (for example a CSS styling specialist) using QLoRA via Unsloth on a free Colab or Kaggle GPU, then compare it with the base model on that role.

## 7. Event log and visualization

### 7.1 Event schema

The event log is append-only and is the single source of truth. Every event carries:

| Field | Description |
| --- | --- |
| `timestamp` | Event time |
| `agent_id` | Agent that caused the event |
| `event_type` | One of the types below |
| `target` | Page section or file affected |
| `payload` | Short structured details |

### 7.2 Event types and cursor mapping

| Event | Cursor behavior |
| --- | --- |
| `agent_spawned` | Cursor appears with the role color |
| `task_claimed` | Cursor moves to the targeted page section |
| `file_edit` | Typing or highlight on that section |
| `signal_emitted` | Short pulse or trail at the target |
| `test_run` | Cursor moves to the test panel or preview |
| `test_failed` | Target section flashes red |
| `fix_applied` | Target section flashes green |
| `agent_failed` | Cursor fades out, failure marker shown |
| `agent_recovered` | Replacement cursor takes over the task |
| `task_done` | Section marked complete, progress updates |

### 7.3 Streaming and replay

- The API streams events to the interface over WebSocket.
- The interface only replays events; it never invents cursor motion.
- Replay mode re-reads stored events from the database with the original timing.
- Because the GPU serializes model calls, display of parallel cursors is derived from logged event timestamps, not from true parallel execution.

### 7.4 Section targeting

Generated pages must expose stable section identifiers (for example `data-section="hero"`) so events can map to preview regions. Agents include the section id in the `target` field.

## 8. API layer

Endpoint contracts will be finalized in the API specification. Minimum surface:

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/builds` | Start a build from prompt or screenshot (FR1) |
| POST | `/builds/{id}/rebuild` | Rebuild with a modified prompt (FR10) |
| GET | `/builds/{id}` | Build status, tasks, scores |
| GET | `/builds/{id}/preview/...` | Serve generated site preview |
| WS | `/builds/{id}/events` | Live event stream (FR9) |
| GET | `/builds/{id}/events` | Stored events for replay |
| GET | `/agents/{id}` | Current task and recent actions (UC3) |
| POST | `/agents/{id}/kill` and `/pause` | Failure injection (FR11) |
| POST | `/benchmarks` | Run an experiment configuration (FR12) |
| GET | `/benchmarks/{id}/results` | Export results |

## 9. Execution sandbox and testing

### 9.1 Sandbox

- Generated code is written and built only inside a temporary project folder per build.
- File tools reject any path outside that folder (path normalization, no symlink escape).
- No access to personal files. Network access from generated code and build steps is disabled or restricted to the package registry when needed.
- Docker is used only if resources allow; the folder sandbox is the default.
- Sandbox folders are deleted after the build unless the user keeps them.

### 9.2 Automated testing

| Tool | Use |
| --- | --- |
| Playwright | Load pages, check navigation and forms, take screenshots |
| Lighthouse | Performance, accessibility and best-practices scores |
| Visual diff | Compare generated screenshot with reference (SSIM or perceptual hash) |
| Build tooling | Detect compile and runtime errors |

The Testing agent converts failures into bug signals and fix tasks (FR6, FR7). In screenshot mode, the vision loop is: render, screenshot, compare, post visual-difference tasks, repeat until threshold or iteration limit.

## 10. Data storage

Entities to be fully specified in the data model document:

| Entity | Key fields |
| --- | --- |
| `build` | id, mode, prompt, reference image, config, seed, status, timestamps |
| `agent` | id, build, role, model, status, heartbeat |
| `task` | id, build, description, status, owner, lease_expiry, dependencies, priority, retries |
| `artifact` | id, build, path, version, author, content hash |
| `signal` | id, build, type, target, strength, last_reinforced, emitter(s) |
| `score` | id, build, type, value, iteration |
| `event` | id, build, timestamp, agent, type, target, payload |
| `model_call` | id, agent, model, prompt, tokens in/out, latency |
| `experiment_run` | id, system (B1/B2/B3/S), prompt id, repetition, metrics |

Use SQLite for development (with transactions for atomic claims) and PostgreSQL optionally. Task claims must use compare-and-set or row-level locking.

## 11. Baselines and evaluation infrastructure

| ID | System | Technical note |
| --- | --- | --- |
| B1 | Single Qwen agent, one-shot | One prompt, one generation, no repair |
| B2 | Single Qwen agent with test-and-fix loop | Same tools as swarm Testing agent, one agent |
| B3 | Centralized orchestrator pipeline | Previous design with orchestrator assigning tasks |
| S | Decentralized swarm | This project |

Requirements for the benchmark harness:

- Same model family (Qwen 3.5), same test set, same sandbox and same metrics for all systems.
- Fixed seeds, saved prompts and saved model versions.
- At least three runs per configuration; report mean and variation.
- Metrics captured: build success, test pass rate, Lighthouse scores, visual similarity, total time, model calls, tokens, bugs found and fixed, recovery time and success.
- Failure injection (E3) via the kill and pause controls at configurable build progress points.
- Results exported (for example CSV or JSON) and shown in the evaluation dashboard.

## 12. Technology stack

| Component | Technology |
| --- | --- |
| AI model | Qwen 3.5 (local small models, optional Qwen3.5-Plus) |
| Model serving | Ollama or llama.cpp |
| Frontend | React, JavaScript, CSS |
| Cursor visualization | JavaScript, CSS, SVG, WebSocket |
| Backend | Python, FastAPI |
| Swarm runtime | Custom blackboard and agent runner (asyncio) |
| Database | SQLite for development, PostgreSQL optional |
| Testing tools | Playwright, Lighthouse |
| Code execution | Temporary sandbox folder, Docker only if resources allow |
| Version control | Git and GitHub |
| Fine-tuning (optional) | Unsloth with QLoRA on Colab or Kaggle |

## 13. Hardware and resource plan

Development machine: Intel i5 laptop, NVIDIA RTX 4050 laptop GPU (typically 6 GB VRAM; verify on the device), about 256 GB storage with part already used.

| Constraint | Technical response |
| --- | --- |
| Limited VRAM | 4-bit quantized models; one shared model instance; the 9B model only for single hard decisions, one at a time |
| Limited disk | Keep only two or three model files on disk |
| No parallel model execution | Request queue; agents take turns; display parallelism derived from event log |
| Limited CPU/RAM | Avoid heavy Docker setups; folder sandbox first |
| Slow fine-tuning and large benchmarks | Run on Colab or Kaggle |

## 14. Non-functional technical requirements

| ID | Category | Technical requirement | PRD trace |
| --- | --- | --- | --- |
| TR1 | Performance | A simple site builds in a few minutes on the target laptop; model calls are asynchronous so the UI and API stay responsive | NFR1 |
| TR2 | Reliability | Lease expiry plus heartbeat returns work from a failed agent to the pool; the build completes after one injected failure | NFR2 |
| TR3 | Observability | Every model call, decision, action and score is written to the event log or `model_call` table | NFR3 |
| TR4 | Reproducibility | Seeds, prompts, model names and versions, and runtime config stored per build and per experiment run | NFR4 |
| TR5 | Security | Sandbox path enforcement, no personal file access, restricted network, generated code never executed outside the sandbox | NFR5 |
| TR6 | Portability | Entire stack runs on the target laptop using quantized local models; hosted API is optional | NFR6 |
| TR7 | Usability | Single command or one-click start; build starts from the UI in under a minute | NFR7 |
| TR8 | Atomicity | Task claims, artifact version writes and signal updates are transactional | FR3, FR4 |
| TR9 | Determinism aids | Model temperature and seed configurable; experiments use fixed settings | NFR4 |

## 15. Requirements traceability

| PRD requirement | Primary technical sections |
| --- | --- |
| FR1 | 3.3, 8 |
| FR2 | 3.3, 4 |
| FR3 | 4.3, 4.4, 10 |
| FR4 | 4.1, 4.6, 10 |
| FR5 | 9 |
| FR6, FR7 | 5, 9.2 |
| FR8 | 7, 10 |
| FR9 | 7, 8 |
| FR10 | 8 |
| FR11 | 4.4, 8, 11 |
| FR12 | 11 |
| NFR1–NFR7 | 13, 14 |

## 16. Technical risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Small models produce invalid JSON or weak code | Failed actions, low quality | Schema validation, bounded retries, 4B/9B for hard roles, test-and-fix loops, optional Qwen3.5-Plus |
| GPU memory or speed limits | Slow builds | Quantization, one shared model, short prompts, limited agent count, request queue |
| Race conditions on claims or files | Duplicate work, corrupted artifacts | Atomic claims, optimistic versioning, Integration agent |
| Infinite loops or oscillating fixes | Unstable runs | Iteration, retry and time limits |
| Signal tuning (decay, bid weights) poorly chosen | Poor coordination | Make parameters configurable; tune on a small pilot set |
| Generated code escapes sandbox | Security | Path validation, restricted network, temp folder, optional container |
| Preview/cursor mismatch | Misleading visualization | Stable section ids; cursors driven only by logged events |
| Model names or sizes change | Setup problems | Verify the current model list and quantized builds before downloading |

## 17. Technical open questions

1. Which exact Qwen 3.5 sizes and quantized builds are available and fit in 6 GB VRAM?
2. Ollama or llama.cpp: which gives better concurrency and vision support on the target GPU?
3. How many concurrent model requests can the GPU serve before latency becomes unacceptable?
4. What lease timeout and heartbeat interval balance fast recovery against false expiry on a slow GPU?
5. SSIM or perceptual hash (or both) for the visual similarity metric?
6. Is SQLite sufficient for atomic claims under the expected agent count, or is PostgreSQL needed?

## 18. Glossary

- **Blackboard:** shared memory that agents read and write to coordinate.
- **Stigmergy:** indirect coordination through marks left in a shared environment.
- **Lease:** a time-limited claim on a task that expires if the agent stalls.
- **Heartbeat:** periodic signal from an agent that renews its lease.
- **Signal:** short blackboard message that influences other agents; strength decays over time.
- **Event log:** append-only record of every agent action, used for visualization and analysis.
- **Optimistic versioning:** writes name the version they are based on and are rejected if stale.
- **Quantization:** compressing a model to use less memory, for example 4-bit.
