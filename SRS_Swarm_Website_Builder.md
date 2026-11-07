# Software Requirements Specification (SRS)

# Swarm Website Builder

*Decentralized multi-agent website generation powered by Qwen 3.5*

| Field | Value |
| --- | --- |
| Prepared by | [Your name] |
| Document | Software Requirements Specification |
| Version | 1.0 |
| Date | November 2026 |
| Status | Draft for mentor review |
| Companion documents | Project document v1.0, PRD v1.0, TRD v1.0 |

---

## 1. Introduction

### 1.1 Purpose

This SRS specifies the software requirements of the Swarm Website Builder as numbered, testable statements. It expands the functional requirements FR1–FR12 and non-functional requirements NFR1–NFR7 from the PRD, using the architecture in the TRD. It is intended for the developer, mentor and evaluators, and is the basis for the test and evaluation plan.

### 1.2 Scope

Swarm Website Builder generates websites from a natural-language prompt or a reference screenshot using many Qwen 3.5 agents that coordinate through a shared blackboard with no central controller. It provides live cursor visualization, automated testing and fixing, failure injection and a benchmark harness.

Out of scope: training models from scratch, production hosting of generated sites, multi-user accounts for the builder, and non-web outputs.

### 1.3 Definitions

| Term | Meaning |
| --- | --- |
| Swarm | Many simple agents whose combined behavior emerges from local interactions |
| Agent | A Qwen 3.5 instance with a role-specific prompt, memory and tools |
| Blackboard | Shared memory (goal, tasks, artifacts, signals, scores) used for coordination |
| Task | A unit of work with status, owner, dependencies and priority |
| Artifact | A versioned file or spec produced by an agent |
| Signal | A short blackboard message whose strength decays over time |
| Lease | A time-limited claim on a task that expires if the agent stalls |
| Event | A structured record of one agent action in the append-only event log |
| Build | One run of the system from a goal to a finished or failed site |
| Seeding | The one-time splitting of the goal into initial tasks |
| Baseline | B1, B2 or B3 comparison system |

### 1.4 Requirement conventions

- "Shall" marks a mandatory requirement. "Should" marks a desirable one.
- IDs: **REQ-** functional, **NFR-** non-functional, **IR-** interface, **DR-** data, **CR-** constraint.
- Priority: **M** = Must, **S** = Should, **C** = Could.
- Each requirement has a verification method: **T** = test, **D** = demonstration, **I** = inspection, **A** = analysis.

### 1.5 References

- Swarm Website Builder project document v1.0
- PRD v1.0 and TRD v1.0

## 2. Overall description

### 2.1 Product perspective

A self-contained local system made of a React interface, a FastAPI service, a Python asyncio swarm runtime, local Qwen 3.5 models served by Ollama or llama.cpp, a temporary execution sandbox and SQLite (or PostgreSQL) storage. Qwen3.5-Plus through a hosted API is optional.

### 2.2 Product functions (summary)

1. Accept a prompt or screenshot and create a build.
2. Seed tasks from the goal.
3. Let agents claim tasks by bidding with leases, and coordinate through artifacts and signals.
4. Generate, build, preview and test the site, and auto-create fix tasks.
5. Log every action and visualize it as live cursors.
6. Rebuild with a modified prompt.
7. Inject failures and recover.
8. Run benchmarks against baselines and export results.

### 2.3 User classes

| User class | Description |
| --- | --- |
| Builder user (developer or student) | Starts builds, watches the swarm, inspects agents, rebuilds |
| Researcher | Runs benchmarks, injects failures, exports results |
| Evaluator | Reviews behavior, replay and results |

### 2.4 Operating environment

Laptop with Intel i5 CPU, NVIDIA RTX 4050 laptop GPU (typically 6 GB VRAM, to be verified), about 256 GB storage; modern web browser; Python, Node.js, Ollama or llama.cpp. Colab or Kaggle for fine-tuning and large benchmarks.

### 2.5 Constraints

| ID | Constraint |
| --- | --- |
| CR-1 | All agents shall use Qwen 3.5 models as their reasoning engine. |
| CR-2 | Models shall be 4-bit quantized where run locally. |
| CR-3 | Only one model instance shall be loaded at a time and shared by agents through role prompts. |
| CR-4 | Generated code shall run only inside a temporary sandbox. |
| CR-5 | Exact Qwen 3.5 sizes and quantized builds shall be verified before download. |

### 2.6 Assumptions and dependencies

- The target GPU can run a 4B quantized model; this must be verified.
- Playwright and Lighthouse are installable on the development machine.
- Hosted Qwen3.5-Plus is optional and is not required for any Must requirement.

## 3. System features and functional requirements

### 3.1 Goal input (FR1)

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-1.1 | The system shall accept a natural-language text prompt as the build goal. | M | T |
| REQ-1.2 | The system shall accept an uploaded reference screenshot (PNG or JPEG) as the build goal. | M | T |
| REQ-1.3 | The system shall reject empty input and unsupported file types with a clear message. | M | T |
| REQ-1.4 | The system shall write the goal and any reference image to the blackboard Goal zone. | M | T |
| REQ-1.5 | The system shall assign each build a unique identifier and store its mode, prompt, config and seed. | M | T |
| REQ-1.6 | The system shall allow a prompt and a screenshot to be submitted together. | C | T |

### 3.2 Task seeding (FR2)

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-2.1 | The system shall create initial tasks by a Qwen call that splits the goal into units of work. | M | T |
| REQ-2.2 | Seeding shall be performed by an ordinary agent as a one-time action, and that agent shall gain no authority over other agents. | M | I |
| REQ-2.3 | Each seeded task shall have a description, status `open`, priority and dependencies. | M | T |
| REQ-2.4 | If seeding output is invalid, the system shall retry a bounded number of times and then fail the build with a logged reason. | M | T |
| REQ-2.5 | After seeding, no component shall assign tasks to agents. | M | I |

### 3.3 Task allocation, bidding and leases (FR3)

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-3.1 | Each idle agent shall compute a bid for each open task it can see, based on role match, current load and past success on similar tasks. | M | T |
| REQ-3.2 | The highest bid shall win the claim. Ties shall be broken by a fixed, logged rule. | M | T |
| REQ-3.3 | A claim shall be atomic: two agents shall never hold the same task simultaneously. | M | T |
| REQ-3.4 | A claim shall be a lease with a configurable timeout. | M | T |
| REQ-3.5 | A working agent shall renew its lease by heartbeat. | M | T |
| REQ-3.6 | If a lease expires, the task shall return to `open` and its owner shall be cleared. | M | T |
| REQ-3.7 | A task shall not be claimable until its dependencies are `done`. | M | T |
| REQ-3.8 | A task shall have a retry limit. When exceeded, it shall be marked `failed` and raised as a blocking signal. | M | T |
| REQ-3.9 | Task status shall follow the lifecycle: open, claimed, in progress, in review, done, failed. Invalid transitions shall be rejected. | M | T |

### 3.4 Artifacts and signals (FR4)

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-4.1 | Agents shall read and write artifacts (files, design specs, API routes, schemas) on the blackboard. | M | T |
| REQ-4.2 | Every artifact write shall create a new version and name the version it is based on. | M | T |
| REQ-4.3 | A write based on a stale version shall be rejected, and the agent shall be told to re-read. | M | T |
| REQ-4.4 | If two agents edit the same file, the Integration agent shall merge the changes or post a conflict task. | M | T |
| REQ-4.5 | Agents shall emit signals (for example `need_styling`, `bug_found`, `needs_review`, `blocked`) with a type, target and strength. | M | T |
| REQ-4.6 | Signal strength shall decay over time according to a configurable half-life. | M | T |
| REQ-4.7 | When several agents emit the same signal for the same target, its strength shall increase. | M | T |
| REQ-4.8 | Signals below a minimum strength shall be pruned. | S | T |
| REQ-4.9 | Agents shall give priority to stronger signals when deciding what to do. | M | A |
| REQ-4.10 | Design choices shall be decided by proposals, reviewer critiques and a vote. | S | D |
| REQ-4.11 | Agents shall decide only from what they read on the blackboard. | M | I |

### 3.5 Agent behavior and Qwen usage

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-5.1 | Each agent shall run the loop: observe, decide, act, report, repeat. | M | T |
| REQ-5.2 | Every agent decision shall be produced by a Qwen 3.5 call. | M | I |
| REQ-5.3 | Agents shall return actions as JSON that the runtime validates before execution. | M | T |
| REQ-5.4 | Invalid JSON shall trigger a bounded retry, then release of the task. | M | T |
| REQ-5.5 | Actions naming unknown tools or paths outside the sandbox shall be rejected and logged. | M | T |
| REQ-5.6 | The system shall support at least these roles: UI/UX, Frontend, Backend, Database, Testing, Integration, Reviewer. | M | D |
| REQ-5.7 | A build shall be able to run with a subset of three to four roles. | M | D |
| REQ-5.8 | Roles shall be defined by configuration (system prompt, tools, bid profile) so roles can be added or removed without changing the runtime. | S | I |
| REQ-5.9 | Qwen 3.5 vision shall be used to read a reference screenshot and to compare it with the generated page. | M | T |
| REQ-5.10 | The system shall route each call to the model tier configured for that agent or step (0.8B–2B, 4B, 9B or optional hosted Qwen3.5-Plus). | S | T |
| REQ-5.11 | No agent shall have authority to assign tasks to, or override, other agents. | M | I |

### 3.6 Website generation, build and preview (FR5)

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-6.1 | The system shall generate a multi-page site from a prompt. | M | D |
| REQ-6.2 | The system shall support static sites (HTML, CSS, JavaScript) and light dynamic sites (React, simple FastAPI API, database). | M | D |
| REQ-6.3 | Generated files shall be written only inside the build's sandbox folder. | M | T |
| REQ-6.4 | The system shall build the site and report build errors as bug signals. | M | T |
| REQ-6.5 | The system shall serve a live preview of the site to the interface. | M | T |
| REQ-6.6 | The preview shall refresh when artifacts change. | S | T |
| REQ-6.7 | Generated pages shall expose stable section identifiers so events can target preview regions. | M | I |

### 3.7 Testing and screenshot comparison (FR6)

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-7.1 | The Testing agent shall build the site, run browser tests, and take screenshots using Playwright. | M | T |
| REQ-7.2 | The system shall run Lighthouse and record performance, accessibility and best-practices scores. | S | T |
| REQ-7.3 | In screenshot mode, the system shall compute a visual similarity score between the generated page and the reference (for example SSIM or perceptual hash). | M | T |
| REQ-7.4 | Test results and similarity scores shall be written to the Scores zone with the iteration number. | M | T |
| REQ-7.5 | In screenshot mode, the system shall repeat render, screenshot, compare and fix until the similarity threshold or the iteration limit is reached. | M | T |
| REQ-7.6 | The similarity threshold and iteration limit shall be configurable. | M | T |

### 3.7.1 Bug and fix handling (FR7)

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-8.1 | When a build or test fails, the Testing agent shall post a `bug_found` signal and a fix task referencing the failing section or file. | M | T |
| REQ-8.2 | When a visual difference exceeds tolerance, the Testing agent shall post a visual-difference task naming the affected section. | M | T |
| REQ-8.3 | Fix tasks shall be claimed and processed through the same bidding mechanism as other tasks. | M | T |
| REQ-8.4 | After a fix, the Testing agent shall re-run the relevant tests and record the result. | M | T |
| REQ-8.5 | A build shall be complete only when: the site builds, all tests pass, no strong bug signals remain, and (screenshot mode) similarity is above threshold or the iteration limit is reached. | M | T |
| REQ-8.6 | If the global time budget or iteration limit is reached before completion, the build shall end with a status reporting what remains unfinished. | M | T |

### 3.8 Event logging (FR8)

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-9.1 | Every agent action shall be appended to an event log as a structured event. | M | T |
| REQ-9.2 | Each event shall contain timestamp, agent id, event type, target (section or file) and a short payload. | M | T |
| REQ-9.3 | The system shall support at least these event types: `agent_spawned`, `task_claimed`, `file_edit`, `signal_emitted`, `test_run`, `test_failed`, `fix_applied`, `agent_failed`, `agent_recovered`, `task_done`. | M | T |
| REQ-9.4 | The event log shall be append-only; events shall not be modified or deleted during a build. | M | T |
| REQ-9.5 | Every Qwen call shall record model name and version, parameters, token counts and latency. | M | T |
| REQ-9.6 | Event order shall be preserved and reproducible on replay. | M | T |

### 3.9 Live visualization (FR9)

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-10.1 | The interface shall show one animated cursor per agent. | M | D |
| REQ-10.2 | A cursor shall move or change only in response to a logged event. | M | I |
| REQ-10.3 | Cursor behavior shall follow the event mapping: appears on spawn, moves to the target section on claim, shows typing on file edit, pulses on signal, moves to test panel on test run, flashes red on test failure, flashes green on fix, fades with failure marker on agent failure, replacement cursor on recovery, marks section complete on task done. | M | D |
| REQ-10.4 | The interface shall provide a live preview with cursors, task board, agent list with status, scrolling log, and progress bar. | M | D |
| REQ-10.5 | Clicking a cursor shall show that agent's current task and recent actions. | M | D |
| REQ-10.6 | The interface shall provide a replay mode that re-plays stored events. | S | D |
| REQ-10.7 | The interface shall receive events over WebSocket in real time. | M | T |
| REQ-10.8 | The interface shall show an evaluation dashboard of benchmark results. | S | D |
| REQ-10.9 | The interface shall remain responsive while agents run. | M | T |

### 3.10 Rebuild (FR10)

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-11.1 | The user shall be able to start a rebuild with a modified prompt. | S | T |
| REQ-11.2 | A rebuild shall create a new build record linked to the original build and shall not alter the original's events. | S | T |
| REQ-11.3 | The system shall show the new build in the same interface. | S | D |

### 3.11 Failure injection and recovery (FR11)

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-12.1 | A researcher shall be able to kill an agent during a build. | M | T |
| REQ-12.2 | A researcher shall be able to pause an agent during a build. | S | T |
| REQ-12.3 | Failure injection shall be available from the interface and the API, and shall be triggerable at a configured build progress point for experiments. | S | T |
| REQ-12.4 | When an agent is killed, its lease shall expire and its task shall return to `open`. | M | T |
| REQ-12.5 | Another agent shall be able to claim the released task and continue. | M | T |
| REQ-12.6 | The system shall log `agent_failed` and `agent_recovered` events, and shall record recovery time. | M | T |
| REQ-12.7 | The build shall complete successfully after one injected agent failure. | M | T |

### 3.12 Benchmarking (FR12)

| ID | Requirement | Pri | Ver |
| --- | --- | --- | --- |
| REQ-13.1 | The system shall run the same test set on B1 (single agent, one-shot), B2 (single agent with test-and-fix loop), B3 (centralized orchestrator pipeline) and S (swarm). | M | T |
| REQ-13.2 | All systems shall use Qwen 3.5 models only. | M | I |
| REQ-13.3 | The test set shall contain 10 to 20 prompts of increasing difficulty and 5 to 10 reference screenshots. | M | I |
| REQ-13.4 | Each configuration shall be run at least three times. | M | T |
| REQ-13.5 | The system shall record: build success, test pass rate, Lighthouse scores, visual similarity, total time, number of model calls, tokens, bugs found and fixed, recovery time and success. | M | T |
| REQ-13.6 | The system shall support experiments E1 (all systems), E2 (small-model swarm vs one larger Qwen model), E3 (failure injection) and E4 (screenshot mode with and without the vision loop). | M | D |
| REQ-13.7 | The system shall report averages and variation per configuration. | M | T |
| REQ-13.8 | The system shall export results in a machine-readable format such as CSV or JSON. | M | T |

## 4. External interface requirements

### 4.1 User interface

| ID | Requirement |
| --- | --- |
| IR-1 | The interface shall provide a prompt field, a screenshot upload control and a start button on the first screen. |
| IR-2 | The build screen shall show the live preview with cursors, task board, agent list, log and progress bar. |
| IR-3 | The interface shall provide controls for rebuild, replay and failure injection. |
| IR-4 | The interface shall provide a benchmark view with comparison tables and charts. |
| IR-5 | Cursors shall use role-specific colors, and failure and success states shall not rely on color alone (include an icon or label). |

### 4.2 API interfaces

| ID | Requirement |
| --- | --- |
| IR-6 | The API shall expose REST endpoints to start a build, rebuild, get status, serve preview, inject failure, run benchmarks and fetch results. |
| IR-7 | The API shall expose a WebSocket endpoint that streams build events in order. |
| IR-8 | The API shall return clear error codes and messages for invalid input. |

### 4.3 Model interface

| ID | Requirement |
| --- | --- |
| IR-9 | The model layer shall call Qwen 3.5 through Ollama or llama.cpp over a local interface. |
| IR-10 | The model layer shall optionally call hosted Qwen3.5-Plus for designated hard steps, and shall work without it. |
| IR-11 | The model layer shall support image input for vision calls. |

### 4.4 Sandbox and tool interfaces

| ID | Requirement |
| --- | --- |
| IR-12 | Tools exposed to agents shall be limited to: read/write file in sandbox, run build, run test, take screenshot, read blackboard, write blackboard. |
| IR-13 | The sandbox interface shall normalize paths and reject any path outside the build's folder. |

## 5. Data requirements

| ID | Requirement |
| --- | --- |
| DR-1 | The system shall persist builds, agents, tasks, artifacts, signals, scores, events, model calls and experiment runs. |
| DR-2 | Each task shall store status, owner, lease expiry, dependencies, priority and retry count. |
| DR-3 | Each artifact shall store path, version, author and content hash. |
| DR-4 | Each signal shall store type, target, current strength and last reinforcement time. |
| DR-5 | Each event shall store timestamp, agent id, type, target and payload. |
| DR-6 | Each experiment run shall store system (B1, B2, B3, S), prompt id, repetition number, seed, model versions and metrics. |
| DR-7 | Task claims and artifact version writes shall be transactional. |
| DR-8 | SQLite shall be supported for development; PostgreSQL may be supported. |

## 6. Non-functional requirements

### 6.1 Performance (NFR1)

| ID | Requirement | Ver |
| --- | --- | --- |
| NFR-1.1 | A simple site shall build in a few minutes on the target laptop. The exact target time shall be fixed after Phase 1 measurements. | T |
| NFR-1.2 | Model calls shall be asynchronous so that the interface and API remain responsive. | T |
| NFR-1.3 | Event delivery from the log to the interface shall be near real time during a build. | T |
| NFR-1.4 | The runtime shall queue model requests so GPU memory is not exceeded. | T |

### 6.2 Reliability (NFR2)

| ID | Requirement | Ver |
| --- | --- | --- |
| NFR-2.1 | The build shall complete after one agent failure. | T |
| NFR-2.2 | Iteration, retry and time limits shall prevent infinite loops. | T |
| NFR-2.3 | A crash of one agent shall not corrupt blackboard state or artifacts. | T |
| NFR-2.4 | The system shall recover blackboard state from storage after a runtime restart. | S |

### 6.3 Observability (NFR3)

| ID | Requirement | Ver |
| --- | --- | --- |
| NFR-3.1 | Every decision, action and score shall be logged. | I |
| NFR-3.2 | A build shall be fully reconstructable from its event log. | T |

### 6.4 Reproducibility (NFR4)

| ID | Requirement | Ver |
| --- | --- | --- |
| NFR-4.1 | Experiments shall use fixed seeds, saved prompts and saved model versions. | I |
| NFR-4.2 | Temperature and seed shall be configurable per build. | T |
| NFR-4.3 | Runtime configuration (bid weights, decay, lease timeout) shall be stored with each run. | I |

### 6.4.1 Security (NFR5)

| ID | Requirement | Ver |
| --- | --- | --- |
| NFR-5.1 | Generated code shall run only in a temporary sandbox folder or minimal container. | T |
| NFR-5.2 | Generated code shall have no access to personal files. | T |
| NFR-5.3 | Network access from generated code and build steps shall be disabled or restricted. | T |
| NFR-5.4 | Sandbox folders shall be removed after the build unless the user keeps them. | T |
| NFR-5.5 | Uploaded images shall be validated for type and size. | T |
| NFR-5.6 | API keys for the optional hosted model shall be stored outside the code repository. | I |

### 6.5 Portability (NFR6)

| ID | Requirement | Ver |
| --- | --- | --- |
| NFR-6.1 | The system shall run on a laptop with a small GPU using quantized models. | D |
| NFR-6.2 | The system shall run without the hosted API. | T |
| NFR-6.3 | Heavy Docker setups shall not be required. | I |

### 6.6 Usability (NFR7)

| ID | Requirement | Ver |
| --- | --- | --- |
| NFR-7.1 | A new user shall be able to start a build in under a minute. | T |
| NFR-7.2 | Errors shall be shown with a clear message and a suggested action. | T |
| NFR-7.3 | The system shall document setup and a first-run guide. | I |

### 6.7 Maintainability

| ID | Requirement | Ver |
| --- | --- | --- |
| NFR-8.1 | Roles, model tiers and runtime parameters shall be configurable without code changes. | I |
| NFR-8.2 | Code shall be version controlled in Git and hosted on GitHub. | I |

## 7. Verification and acceptance

### 7.1 Acceptance criteria

| ID | Acceptance criterion | Related requirements |
| --- | --- | --- |
| AC-1 | From a prompt, the system produces a multi-page site that builds and previews. | REQ-1.1, 6.1, 6.5 |
| AC-2 | From a screenshot, the system produces a site whose similarity score improves across iterations. | REQ-1.2, 7.3, 7.5 |
| AC-3 | Inspection of the runtime shows no component assigning tasks to agents. | REQ-2.5, 5.11 |
| AC-4 | Every agent decision in the log traces to a Qwen 3.5 call. | REQ-5.2, 9.5 |
| AC-5 | Every cursor movement in the interface maps to a logged event. | REQ-10.2, 10.3 |
| AC-6 | After a killed agent, the build still completes. | REQ-12.4, 12.5, 12.7 |
| AC-7 | The benchmark compares B1, B2, B3 and S with three runs each and exports results. | REQ-13.1, 13.4, 13.8 |
| AC-8 | Generated code cannot read or write outside the sandbox. | REQ-6.3, NFR-5.2 |

### 7.2 Traceability matrix

| PRD requirement | SRS requirements |
| --- | --- |
| FR1 | REQ-1.1 to 1.6 |
| FR2 | REQ-2.1 to 2.5 |
| FR3 | REQ-3.1 to 3.9 |
| FR4 | REQ-4.1 to 4.11, REQ-5.x |
| FR5 | REQ-6.1 to 6.7 |
| FR6 | REQ-7.1 to 7.6 |
| FR7 | REQ-8.1 to 8.6 |
| FR8 | REQ-9.1 to 9.6 |
| FR9 | REQ-10.1 to 10.9 |
| FR10 | REQ-11.1 to 11.3 |
| FR11 | REQ-12.1 to 12.7 |
| FR12 | REQ-13.1 to 13.8 |
| NFR1 to NFR7 | NFR-1.x to NFR-7.x |

## 8. Open issues

1. Exact build-time target for a "simple site" (NFR-1.1) to be set after Phase 1 measurements.
2. Default similarity threshold and iteration limit for screenshot mode.
3. Default lease timeout, heartbeat interval, signal half-life and bid weights.
4. Confirmed Qwen 3.5 sizes and quantized builds that fit the target GPU.
5. Choice of similarity metric (SSIM, perceptual hash or both).
6. Whether use of the optional hosted Qwen3.5-Plus is acceptable under CR-1 for the final evaluation.
