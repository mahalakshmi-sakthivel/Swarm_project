# Swarm Website Builder

*Decentralized multi-agent website generation powered by Qwen 3.5*

Prepared by: \[Your name\] | Version 1.0 | November 2026 | Status: Draft for mentor review

## 1. Executive summary

Swarm Website Builder is a system in which many Qwen 3.5 agents build a website together without a central controller. The user provides a natural-language prompt or a reference screenshot. The agents coordinate through a shared blackboard: they claim tasks, leave signals for each other, write code, test the result and fix errors. A live visualization shows one animated cursor per agent, driven by real events from the system rather than decorative animation.

The project has two goals:

- **Engineering goal:** a working prompt-to-website and screenshot-to-website builder.
- **Research goal:** measure whether a decentralized swarm of small Qwen 3.5 models can match or beat a single agent or a centralized pipeline on quality, cost and resilience.

## 2. Background and motivation

Tools such as Lovable, v0, Bolt and Cursor already generate websites from prompts, using a single model or a fixed pipeline. They do not show how the work is divided, and they do not give evidence about whether a decentralized multi-agent approach is better.

The first version of this project used a central orchestrator that assigned tasks to labeled agents, with Qwen used only for the initial planning. Mentor feedback identified two weaknesses:

1. A central orchestrator makes the system a pipeline, not a swarm.
2. Qwen 3.5 was used only for orchestration, not as the intelligence inside every agent.

This revised design fixes both. There is no central controller, and every agent reasons with Qwen 3.5.

## 3. Vision and objectives

**Vision:** a website that builds itself through the visible, self-organized cooperation of many small AI agents.

| ID | Objective |
| --- | --- |
| O1 | Generate a multi-page website from a natural-language prompt. |
| O2 | Reconstruct a website from a reference screenshot and refine it until it visually matches. |
| O3 | Coordinate agents without a central controller, using a shared blackboard. |
| O4 | Use Qwen 3.5 as the reasoning engine of every agent, including vision. |
| O5 | Visualize real agent activity live through swarm cursors. |
| O6 | Evaluate the swarm against baselines with measurable metrics. |
| O7 | Demonstrate resilience by recovering from injected agent failures. |

## 4. Core concept: why this is a swarm

A swarm is a set of simple agents that follow local rules and interact through a shared environment. The overall behavior emerges from these interactions instead of being dictated by a boss.

| Pipeline (previous design) | Swarm (this design) |
| --- | --- |
| Central orchestrator assigns tasks | Agents choose tasks themselves |
| Fixed order of steps | Order emerges from signals and needs |
| One failed agent stops the flow | Failed work returns to the pool and others take it |
| Intelligence in the controller | Intelligence in every agent |
| Hard to show emergence | Emergence is visible in cursors and logs |

**Design principles**

- **Stigmergy:** agents communicate indirectly by leaving marks (tasks, signals, artifacts) on a shared blackboard, like ants leaving pheromones.
- **Local decisions:** each agent decides using only what it reads on the blackboard.
- **Redundancy:** any agent can take over unfinished work.
- **Observability:** every action is logged, so behavior can be replayed and measured.

## 5. Research questions and hypotheses

| ID | Research question | Hypothesis |
| --- | --- | --- |
| RQ1 | Does a swarm produce better websites than one agent working alone? | The swarm gets higher test-pass and visual-match scores. |
| RQ2 | Can a swarm of small Qwen 3.5 models match one larger Qwen 3.5 model? | Comparable quality at lower memory and cost per call. |
| RQ3 | Does the swarm recover from agent failure? | Build still completes with small time overhead. |
| RQ4 | Does a vision-based feedback loop improve screenshot reconstruction? | Visual similarity improves with each iteration. |

## 6. Scope

**In scope**

- Prompt-to-website and screenshot-to-website generation.
- Static and light dynamic sites (HTML, CSS, JavaScript or React, simple API and database).
- Decentralized coordination through a blackboard.
- Real-time cursor visualization, logs and progress tracking.
- Automated testing, error detection and fixing.
- Preview and rebuild.
- Evaluation against baselines.

**Out of scope**

- Training a model from scratch.
- Production hosting or deployment of generated sites.
- Multi-user accounts and collaboration for the builder itself.
- Non-web outputs such as mobile apps.

## 7. Users and use cases

**Users:** students and researchers studying multi-agent systems, developers who want a fast website draft, and evaluators who review the project.

| ID | Use case |
| --- | --- |
| UC1 | User enters a prompt and watches the swarm build the site. |
| UC2 | User uploads a screenshot and gets a matching site. |
| UC3 | User inspects an agent's activity by clicking its cursor. |
| UC4 | User triggers a rebuild with a modified prompt. |
| UC5 | Researcher runs a benchmark and compares swarm and baselines. |
| UC6 | Researcher kills an agent and observes recovery. |

## 8. System architecture

**Layers**

1. **Interface layer (React):** prompt and screenshot input, cursor visualization, task board, log stream, live preview, evaluation dashboard.
2. **API layer (FastAPI):** REST and WebSocket endpoints for starting builds, streaming events and serving previews.
3. **Swarm runtime (Python):** blackboard, agent runner, bidding and lease logic, signal decay, event log.
4. **Model layer:** Qwen 3.5 models served locally through Ollama or llama.cpp, with optional Qwen3.5-Plus through the hosted API for hard steps.
5. **Execution sandbox:** a temporary project folder (or minimal container) where generated code is written, built and tested.
6. **Storage:** SQLite or PostgreSQL for blackboard state, event log and evaluation results.

**High-level data flow**

1. The user submits a prompt or screenshot. The goal is written to the blackboard.
2. A seeding step uses Qwen to split the goal into initial tasks. This is a one-time action by an ordinary agent, not a controller.
3. Agents read the blackboard, bid for tasks that match their role, and claim them.
4. Agents write artifacts (files, designs, API routes) and signals back to the blackboard.
5. Every action is appended to the event log.
6. The Testing agent builds the site, runs tests and screenshots it, then posts bugs and visual-difference tasks.
7. The loop repeats until the completion criteria are met.
8. The event log streams to the interface, which animates the cursors and updates the preview.

## 9. Agent roles

Every agent is Qwen 3.5 with a role-specific system prompt, memory and tools. There is no agent with authority over the others.

| Agent | Responsibility | Reads | Writes |
| --- | --- | --- | --- |
| UI/UX | Layout, design tokens, component structure | Goal, reference image | Design spec, style signals |
| Frontend | Pages and components | Design spec, tasks | HTML, CSS, JS or React files |
| Backend | APIs and logic | Tasks, data schema | FastAPI routes |
| Database | Data model and storage | Tasks, API needs | Schema and seed data |
| Testing | Build, test, screenshot, visual diff | Artifacts | Bug signals, fix tasks, scores |
| Integration | Merge modules and resolve conflicts | Artifacts, conflicts | Integrated project |
| Reviewer | Critique and vote on proposals | Artifacts, proposals | Review signals, votes |

A small build can run with three to four of these roles. Roles can be added or removed without changing the architecture.

## 10. Blackboard and coordination design

**Blackboard zones**

- **Goal:** the user request and reference image.
- **Tasks:** units of work with status, owner, dependencies and priority.
- **Artifacts:** versioned files and specs produced by agents.
- **Signals:** short messages that influence other agents (for example, need\_styling, bug\_found, needs\_review, blocked).
- **Scores:** test results and visual similarity values.

**Task lifecycle:** open, claimed, in progress, in review, done, failed. A failed or expired task returns to open.

**Task allocation by bidding**

- Each idle agent computes a bid for each open task from role match, current load and past success on similar tasks.
- The highest bid wins the claim. Claims are atomic, so two agents cannot hold the same task.
- A claim is a lease with a timeout. If the agent crashes or stalls, the lease expires and the task becomes open again. This is the self-healing mechanism.

**Signals with decay:** each signal has a strength that decays over time and is reinforced when several agents emit the same signal. Agents give priority to strong signals, which imitates pheromone trails.

**Conflict handling:** artifacts use optimistic versioning. If two agents edit the same file, the Integration agent merges the changes or posts a conflict task.

**Collective decisions:** for design choices, several agents post proposals, the Reviewer agents critique them, and a vote selects the winner. Good parts of losing proposals can be merged.

**Agent loop**

1. Observe: read new tasks, signals and artifacts.
2. Decide: ask Qwen what to do next, or bid on a task.
3. Act: call tools (write file, run build, take screenshot, run test).
4. Report: write results and signals to the blackboard and log events.
5. Repeat until no open tasks remain and the completion criteria pass.

**Completion criteria:** the site builds, all tests pass, no strong bug signals remain, and (for screenshot mode) the visual similarity score is above the chosen threshold or the iteration limit is reached.

## 11. Role of Qwen 3.5

Qwen 3.5 is the reasoning engine inside every agent, not only the planner.

- **Reasoning and decisions:** choosing tasks, planning steps, deciding when to ask for help.
- **Code generation:** HTML, CSS, JavaScript, React, Python and SQL.
- **Vision:** reading a reference screenshot and comparing it with the generated page. Qwen 3.5 is natively multimodal, which is why one model family can do both text and image work.
- **Structured output:** agents return actions as JSON so the runtime can execute tool calls reliably.
- **Critique:** reviewing other agents' output and voting.

**Model sizing strategy.** The Qwen 3.5 family includes small models (around 0.8B to 9B parameters), a 27B model and a 397B mixture-of-experts flagship. Exact availability and quantized versions must be checked on Hugging Face or Ollama before download.

| Use | Model | Where it runs |
| --- | --- | --- |
| Simple agents (linting, styling, formatting) | 0.8B to 2B | Local GPU |
| Main agents (frontend, backend, testing) | 4B | Local GPU |
| Hard single decisions, optional | 9B | Local GPU, one at a time |
| Hardest steps, optional | Qwen3.5-Plus | Hosted API |

**Optional fine-tuning:** fine-tune one small Qwen 3.5 model for a single role (for example, a CSS styling specialist) using QLoRA on a free Colab or Kaggle GPU, then compare it with the base model on that role.

## 12. Swarm cursor visualization

The event log is the single source of truth. The interface only replays events, so a cursor moves only when its agent does something real.

| Event | Cursor behavior |
| --- | --- |
| agent\_spawned | Cursor appears with the role color. |
| task\_claimed | Cursor moves to the page section the task targets. |
| file\_edit | Cursor shows typing or highlight on that section. |
| signal\_emitted | A short pulse or trail appears at the target. |
| test\_run | Cursor moves to the test panel or preview. |
| test\_failed | Target section flashes red. |
| fix\_applied | Target section flashes green. |
| agent\_failed | Cursor fades out and a failure marker is shown. |
| agent\_recovered | A replacement cursor takes over the task. |
| task\_done | Section is marked complete and progress updates. |

Every event carries a timestamp, agent id, event type, target (section or file) and a short payload.

**Interface panels:** live preview with cursors, task board, agent list with status, scrolling log, progress bar, replay mode and an evaluation dashboard. Clicking a cursor opens that agent's current task and recent actions.

## 13. Functional requirements (summary)

- FR1: accept a text prompt or an uploaded screenshot.
- FR2: seed tasks from the goal.
- FR3: let agents claim tasks by bidding, with leases and expiry.
- FR4: let agents read and write artifacts and signals.
- FR5: generate, build and preview the website.
- FR6: run automated tests and screenshot comparison.
- FR7: create and process bug and fix tasks automatically.
- FR8: log every agent action as a structured event.
- FR9: render real-time cursors, logs and progress from the event log.
- FR10: support rebuild with a modified prompt.
- FR11: support failure injection (kill or pause an agent).
- FR12: run benchmark experiments and export results.

## 14. Non-functional requirements

- **Performance:** a simple site should build in a few minutes on the target laptop. The interface must stay responsive while agents run.
- **Reliability:** the build must complete after one agent failure.
- **Observability:** every decision, action and score is logged.
- **Reproducibility:** fixed seeds, saved prompts and saved model versions for experiments.
- **Security:** generated code runs only in a temporary sandbox folder (or minimal container) with no access to personal files.
- **Portability:** runs on a laptop with a small GPU using quantized models.
- **Usability:** a new user can start a build in under a minute.

## 15. Technology stack

| Component | Technology |
| --- | --- |
| AI model | Qwen 3.5 (local small models, optional Qwen3.5-Plus) |
| Model serving | Ollama or llama.cpp |
| Frontend | React, JavaScript, CSS |
| Cursor visualization | JavaScript, CSS, SVG, WebSocket |
| Backend | Python, FastAPI |
| Swarm runtime | Custom blackboard and agent runner (asyncio) |
| Database | SQLite for development, PostgreSQL optional |
| Testing tools | Playwright (screenshots and browser tests), Lighthouse |
| Code execution | Temporary sandbox folder, Docker only if resources allow |
| Version control | Git and GitHub |
| Fine-tuning (optional) | Unsloth with QLoRA on Colab or Kaggle |

## 16. Hardware and resource plan

Development machine: Intel i5 laptop, NVIDIA RTX 4050 laptop GPU (typically 6 GB VRAM; verify on the device), about 256 GB storage with part already used.

- Use 4-bit quantized models. Keep only two or three model files on disk.
- Load one model instance and share it across agents through role prompts.
- One GPU cannot run many models in parallel. Agents take turns, or the server handles a few concurrent requests. Cursors still show several agents because the event log decides what is displayed.
- Avoid heavy Docker setups. Use a temporary folder sandbox first.
- Use Colab or Kaggle for fine-tuning and large benchmark runs.

## 17. Evaluation plan

**Systems compared**

| ID | System |
| --- | --- |
| B1 | Single Qwen agent, one-shot generation |
| B2 | Single Qwen agent with a test-and-fix loop |
| B3 | Centralized orchestrator pipeline (previous design) |
| S | Decentralized swarm (this project) |

All systems use Qwen 3.5 only, so differences come from the architecture and not from the model family.

**Test set:** 10 to 20 prompts of increasing difficulty (portfolio, blog, landing page, form with backend, dashboard) and 5 to 10 reference screenshots.

**Metrics**

- Build success rate and test pass rate.
- Lighthouse scores (performance, accessibility, best practices).
- Visual similarity to the reference (for example, SSIM or perceptual hash).
- Total time, number of model calls and tokens used.
- Number of bugs found and fixed automatically.
- Recovery time and success rate after failure injection.

**Experiments**

| ID | Experiment | Answers |
| --- | --- | --- |
| E1 | Compare B1, B2, B3 and S on the full test set | RQ1 |
| E2 | Swarm of small models vs one larger Qwen model | RQ2 |
| E3 | Kill one or more agents mid-build | RQ3 |
| E4 | Screenshot mode with and without the vision loop | RQ4 |

Run each configuration at least three times and report averages and variation.

## 18. Development roadmap

Durations are suggestions and should be adjusted to the real deadline.

| Phase | Focus | Suggested time | Output |
| --- | --- | --- | --- |
| 0 | Setup, model download, repo, documents | 1 week | Running local Qwen, repo, requirement documents |
| 1 | Blackboard and a single Qwen agent | 1 to 2 weeks | One agent builds a simple page |
| 2 | Multi-agent swarm with bidding and leases | 2 weeks | Several agents cooperate without a controller |
| 3 | Event log and cursor visualization | 1 to 2 weeks | Live cursors driven by real events |
| 4 | Testing agent, vision loop, screenshot mode | 2 weeks | Self-correcting site generation |
| 5 | Failure injection and evaluation | 2 weeks | Benchmark results and dashboard |
| 6 | Polish, documentation, demo | 1 week | Final demo, report, presentation |

## 19. Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Small models produce weak code | Low quality | Use the 4B or 9B model for hard roles, add test-and-fix loops, optional Qwen3.5-Plus |
| Limited GPU memory and speed | Slow builds | Quantization, one shared model, short prompts, limited agent count |
| Agents conflict or loop forever | Unstable runs | Leases, iteration limits, version checks, Integration agent |
| Swarm shows no benefit over baselines | Weak research result | Report honestly, analyze why, and present resilience and observability results |
| Generated code is unsafe | Security | Sandbox folder, no network or personal file access |
| Scope grows too large | Missed deadline | Fix a minimum viable build first, add features by phase |
| Model names or sizes change | Setup problems | Verify the current model list before downloading |

## 20. Deliverables

- Working swarm website builder (code in GitHub).
- Live visualization interface.
- Evaluation dashboard and benchmark results.
- Project documents (PRD, TRD and related documents).
- Final report and demo.

## 21. Future work

- Fine-tuned role-specialist Qwen models.
- Larger swarms across multiple machines.
- Support for more frameworks and deployment targets.
- Human-in-the-loop feedback through the cursor interface.
- Learning better bidding strategies from past builds.

## 22. Glossary

- **Swarm:** many simple agents whose combined behavior emerges from local interactions.
- **Blackboard:** shared memory that agents read and write to coordinate.
- **Stigmergy:** indirect coordination through marks left in a shared environment.
- **Lease:** a time-limited claim on a task that expires if the agent stalls.
- **Signal:** a short message on the blackboard that influences other agents.
- **Event log:** ordered record of every agent action, used for visualization and analysis.
- **Quantization:** compressing a model to use less memory, for example 4-bit.

## 23. Document map: how to derive the next documents

| Document | Main inputs from this document |
| --- | --- |
| Product Requirements Document (PRD) | Sections 1, 3, 6, 7, 13, 14, 20 |
| Technical Requirements Document (TRD) | Sections 8, 10, 11, 14, 15, 16 |
| Software Requirements Specification (SRS) | Sections 13, 14 expanded into numbered, testable requirements |
| System architecture and design document | Sections 8, 9, 10, 12 |
| Data model and API specification | Sections 10, 12 (blackboard schema, event schema, endpoints) |
| UX/UI specification | Sections 7, 12 |
| Test and evaluation plan | Sections 5, 14, 17 |
| Project plan and risk register | Sections 18, 19 |
