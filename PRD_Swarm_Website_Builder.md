# Product Requirements Document (PRD)

# Swarm Website Builder

*Decentralized multi-agent website generation powered by Qwen 3.5*

| Field | Value |
| --- | --- |
| Prepared by | [Your name] |
| Document | Product Requirements Document |
| Version | 1.0 |
| Date | November 2026 |
| Status | Draft for mentor review |
| Source | Swarm Website Builder project document v1.0 |

---

## 1. Purpose of this document

This PRD defines **what** the Swarm Website Builder must do, **who** it is for and **how success is judged**. It does not specify implementation detail. Technical choices (blackboard schema, bidding formula, model serving) belong in the Technical Requirements Document (TRD) and the architecture document.

## 2. Product overview

Swarm Website Builder is a system in which many Qwen 3.5 agents build a website together **without a central controller**. The user gives a natural-language prompt or a reference screenshot. The agents coordinate through a shared blackboard: they claim tasks, leave signals for each other, write code, test the result and fix errors.

A live visualization shows one animated cursor per agent. Every cursor movement is driven by a real event from the system, never by decorative animation.

### 2.1 Product vision

A website that builds itself through the visible, self-organized cooperation of many small AI agents.

### 2.2 Product goals

| Goal | Description |
| --- | --- |
| Engineering goal | A working prompt-to-website and screenshot-to-website builder. |
| Research goal | Measure whether a decentralized swarm of small Qwen 3.5 models can match or beat a single agent or a centralized pipeline on quality, cost and resilience. |

## 3. Problem statement and motivation

Tools such as Lovable, v0, Bolt and Cursor generate websites from prompts using a single model or a fixed pipeline. They do not reveal how work is divided, and they provide no evidence on whether a decentralized multi-agent approach is better.

The first version of this project used a central orchestrator assigning tasks to labeled agents, with Qwen used only for initial planning. Mentor feedback found two weaknesses:

1. A central orchestrator makes the system a pipeline, not a swarm.
2. Qwen 3.5 was used only for orchestration, not as the intelligence inside every agent.

This revision addresses both: there is **no central controller**, and **every agent reasons with Qwen 3.5**.

### 3.1 Pipeline vs swarm

| Pipeline (previous design) | Swarm (this product) |
| --- | --- |
| Central orchestrator assigns tasks | Agents choose tasks themselves |
| Fixed order of steps | Order emerges from signals and needs |
| One failed agent stops the flow | Failed work returns to the pool and others take it |
| Intelligence in the controller | Intelligence in every agent |
| Hard to show emergence | Emergence is visible in cursors and logs |

## 4. Objectives

| ID | Objective | Success indicator |
| --- | --- | --- |
| O1 | Generate a multi-page website from a natural-language prompt. | Build succeeds and the site renders with multiple linked pages. |
| O2 | Reconstruct a website from a reference screenshot and refine it until it visually matches. | Visual similarity score rises across iterations and reaches the chosen threshold or iteration limit. |
| O3 | Coordinate agents without a central controller, using a shared blackboard. | No component assigns tasks to agents; all claims happen through the blackboard. |
| O4 | Use Qwen 3.5 as the reasoning engine of every agent, including vision. | Every agent decision and action originates from a Qwen 3.5 call. |
| O5 | Visualize real agent activity live through swarm cursors. | Every cursor movement maps to a logged event. |
| O6 | Evaluate the swarm against baselines with measurable metrics. | Benchmark results exported for B1, B2, B3 and S. |
| O7 | Demonstrate resilience by recovering from injected agent failures. | Build completes after one or more injected failures. |

## 5. Research questions and hypotheses

| ID | Research question | Hypothesis |
| --- | --- | --- |
| RQ1 | Does a swarm produce better websites than one agent working alone? | The swarm gets higher test-pass and visual-match scores. |
| RQ2 | Can a swarm of small Qwen 3.5 models match one larger Qwen 3.5 model? | Comparable quality at lower memory and cost per call. |
| RQ3 | Does the swarm recover from agent failure? | Build still completes with small time overhead. |
| RQ4 | Does a vision-based feedback loop improve screenshot reconstruction? | Visual similarity improves with each iteration. |

If the swarm shows no benefit over baselines, the result is reported honestly, with analysis of why and with the resilience and observability findings.

## 6. Target users and personas

| Persona | Description | Main need |
| --- | --- | --- |
| Student / researcher | Studies multi-agent systems and decentralized coordination. | Observe, replay and measure swarm behavior. |
| Developer | Wants a fast website draft. | Quick prompt-to-site generation with a live preview. |
| Evaluator / mentor | Reviews the project. | Clear evidence of decentralization, Qwen use in every agent and benchmark results. |

## 7. Use cases

| ID | Use case | Primary persona |
| --- | --- | --- |
| UC1 | User enters a prompt and watches the swarm build the site. | Developer, student |
| UC2 | User uploads a screenshot and gets a matching site. | Developer |
| UC3 | User inspects an agent's activity by clicking its cursor. | Student, evaluator |
| UC4 | User triggers a rebuild with a modified prompt. | Developer |
| UC5 | Researcher runs a benchmark and compares swarm and baselines. | Researcher |
| UC6 | Researcher kills an agent and observes recovery. | Researcher, evaluator |

## 8. Scope

### 8.1 In scope

- Prompt-to-website and screenshot-to-website generation.
- Static and light dynamic sites (HTML, CSS, JavaScript or React, simple API and database).
- Decentralized coordination through a blackboard.
- Real-time cursor visualization, logs and progress tracking.
- Automated testing, error detection and fixing.
- Preview and rebuild.
- Evaluation against baselines.

### 8.2 Out of scope

- Training a model from scratch.
- Production hosting or deployment of generated sites.
- Multi-user accounts and collaboration for the builder itself.
- Non-web outputs such as mobile apps.

## 9. Product capabilities (conceptual)

This section describes the product at a behavioral level so that requirements can be understood in context.

### 9.1 Agent roles

Every agent is Qwen 3.5 with a role-specific system prompt, memory and tools. No agent has authority over the others.

| Agent | Responsibility |
| --- | --- |
| UI/UX | Layout, design tokens, component structure |
| Frontend | Pages and components |
| Backend | APIs and logic |
| Database | Data model and storage |
| Testing | Build, test, screenshot, visual diff |
| Integration | Merge modules and resolve conflicts |
| Reviewer | Critique and vote on proposals |

A small build can run with three to four of these roles. Roles can be added or removed without changing the product's behavior model.

### 9.2 Coordination behavior

- Agents read a shared blackboard (goal, tasks, artifacts, signals, scores) and decide what to do from it.
- Tasks are claimed by bidding; claims are time-limited leases, so stalled or crashed work returns to the pool.
- Signals decay over time and strengthen when several agents emit them.
- Conflicting edits are resolved by the Integration agent.
- Design choices are decided through proposals, review and voting.

### 9.3 Completion criteria

A build is complete when the site builds, all tests pass, no strong bug signals remain and, in screenshot mode, the visual similarity score is above the chosen threshold or the iteration limit is reached.

### 9.4 Live visualization

The event log is the single source of truth. The interface replays events, so a cursor moves only when its agent does something real.

Interface panels: live preview with cursors, task board, agent list with status, scrolling log, progress bar, replay mode and an evaluation dashboard. Clicking a cursor opens that agent's current task and recent actions.

## 10. Functional requirements

| ID | Requirement | Priority | Related objective / use case |
| --- | --- | --- | --- |
| FR1 | The system shall accept a text prompt or an uploaded screenshot. | Must | O1, O2 / UC1, UC2 |
| FR2 | The system shall seed initial tasks from the goal through a one-time action by an ordinary agent, not a controller. | Must | O3 |
| FR3 | Agents shall claim tasks by bidding, using leases with expiry. | Must | O3, O7 |
| FR4 | Agents shall read and write artifacts and signals on the blackboard. | Must | O3 |
| FR5 | The system shall generate, build and preview the website. | Must | O1 / UC1 |
| FR6 | The system shall run automated tests and screenshot comparison. | Must | O2 |
| FR7 | The system shall create and process bug and fix tasks automatically. | Must | O1, O2 |
| FR8 | The system shall log every agent action as a structured event (timestamp, agent id, event type, target, payload). | Must | O5, O6 |
| FR9 | The interface shall render real-time cursors, logs and progress from the event log. | Must | O5 / UC1, UC3 |
| FR10 | The user shall be able to rebuild with a modified prompt. | Should | UC4 |
| FR11 | The system shall support failure injection (kill or pause an agent). | Must | O7 / UC6 |
| FR12 | The system shall run benchmark experiments and export results. | Must | O6 / UC5 |

### 10.1 Cursor event behavior

| Event | Required cursor behavior |
| --- | --- |
| agent_spawned | Cursor appears with the role color. |
| task_claimed | Cursor moves to the page section the task targets. |
| file_edit | Cursor shows typing or highlight on that section. |
| signal_emitted | A short pulse or trail appears at the target. |
| test_run | Cursor moves to the test panel or preview. |
| test_failed | Target section flashes red. |
| fix_applied | Target section flashes green. |
| agent_failed | Cursor fades out and a failure marker is shown. |
| agent_recovered | A replacement cursor takes over the task. |
| task_done | Section is marked complete and progress updates. |

## 11. Non-functional requirements

| ID | Category | Requirement |
| --- | --- | --- |
| NFR1 | Performance | A simple site shall build in a few minutes on the target laptop. The interface shall stay responsive while agents run. |
| NFR2 | Reliability | The build shall complete after one agent failure. |
| NFR3 | Observability | Every decision, action and score shall be logged. |
| NFR4 | Reproducibility | Experiments shall use fixed seeds, saved prompts and saved model versions. |
| NFR5 | Security | Generated code shall run only in a temporary sandbox folder (or minimal container) with no access to personal files. |
| NFR6 | Portability | The system shall run on a laptop with a small GPU using quantized models. |
| NFR7 | Usability | A new user shall be able to start a build in under a minute. |

## 12. Success metrics

### 12.1 Product metrics

- Build success rate and test pass rate.
- Lighthouse scores (performance, accessibility, best practices).
- Visual similarity to the reference (for example, SSIM or perceptual hash).
- Total build time, number of model calls and tokens used.
- Number of bugs found and fixed automatically.
- Recovery time and success rate after failure injection.

### 12.2 Evaluation design

All systems use Qwen 3.5 only, so differences come from architecture and not from model family.

| ID | System compared |
| --- | --- |
| B1 | Single Qwen agent, one-shot generation |
| B2 | Single Qwen agent with a test-and-fix loop |
| B3 | Centralized orchestrator pipeline (previous design) |
| S | Decentralized swarm (this project) |

| ID | Experiment | Answers |
| --- | --- | --- |
| E1 | Compare B1, B2, B3 and S on the full test set | RQ1 |
| E2 | Swarm of small models vs one larger Qwen model | RQ2 |
| E3 | Kill one or more agents mid-build | RQ3 |
| E4 | Screenshot mode with and without the vision loop | RQ4 |

Test set: 10 to 20 prompts of increasing difficulty (portfolio, blog, landing page, form with backend, dashboard) and 5 to 10 reference screenshots. Each configuration is run at least three times, reporting averages and variation.

## 13. Constraints and assumptions

- **Hardware:** development on an Intel i5 laptop with an NVIDIA RTX 4050 laptop GPU (typically 6 GB VRAM; to be verified) and limited free storage.
- **Models:** Qwen 3.5 only. Exact model sizes and quantized versions must be verified on Hugging Face or Ollama before download.
- **Compute:** one GPU cannot run many models in parallel, so agents share a model instance and take turns or use a few concurrent requests. The cursors still show several agents because the event log drives the display.
- **Heavy work:** fine-tuning and large benchmark runs use Colab or Kaggle.
- **Timeline:** phase durations are suggestions to be adjusted to the real deadline.

## 14. Release plan

| Phase | Focus | Suggested time | Output |
| --- | --- | --- | --- |
| 0 | Setup, model download, repo, documents | 1 week | Running local Qwen, repo, requirement documents |
| 1 | Blackboard and a single Qwen agent | 1 to 2 weeks | One agent builds a simple page |
| 2 | Multi-agent swarm with bidding and leases | 2 weeks | Several agents cooperate without a controller |
| 3 | Event log and cursor visualization | 1 to 2 weeks | Live cursors driven by real events |
| 4 | Testing agent, vision loop, screenshot mode | 2 weeks | Self-correcting site generation |
| 5 | Failure injection and evaluation | 2 weeks | Benchmark results and dashboard |
| 6 | Polish, documentation, demo | 1 week | Final demo, report, presentation |

A minimum viable build (a few agents, prompt mode, basic cursors) is fixed first; further features are added by phase.

## 15. Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Small models produce weak code | Low quality | Use the 4B or 9B model for hard roles, add test-and-fix loops, optional Qwen3.5-Plus |
| Limited GPU memory and speed | Slow builds | Quantization, one shared model, short prompts, limited agent count |
| Agents conflict or loop forever | Unstable runs | Leases, iteration limits, version checks, Integration agent |
| Swarm shows no benefit over baselines | Weak research result | Report honestly, analyze why, present resilience and observability results |
| Generated code is unsafe | Security | Sandbox folder, no network or personal file access |
| Scope grows too large | Missed deadline | Fix a minimum viable build first, add features by phase |
| Model names or sizes change | Setup problems | Verify the current model list before downloading |

## 16. Deliverables

- Working swarm website builder (code in GitHub).
- Live visualization interface.
- Evaluation dashboard and benchmark results.
- Project documents (PRD, TRD and related documents).
- Final report and demo.

## 17. Future work

- Fine-tuned role-specialist Qwen models.
- Larger swarms across multiple machines.
- Support for more frameworks and deployment targets.
- Human-in-the-loop feedback through the cursor interface.
- Learning better bidding strategies from past builds.

## 18. Open questions for mentor review

1. What visual similarity threshold and iteration limit define "matches" in screenshot mode?
2. Which Qwen 3.5 sizes are confirmed available and runnable on the target GPU?
3. Is optional use of the hosted Qwen3.5-Plus acceptable for the "all agents use Qwen" requirement?
4. What is the real project deadline, so phase durations can be fixed?
5. Is the 10 to 20 prompt and 5 to 10 screenshot test set sufficient for the evaluation?

## 19. Glossary

- **Swarm:** many simple agents whose combined behavior emerges from local interactions.
- **Blackboard:** shared memory that agents read and write to coordinate.
- **Stigmergy:** indirect coordination through marks left in a shared environment.
- **Lease:** a time-limited claim on a task that expires if the agent stalls.
- **Signal:** a short message on the blackboard that influences other agents.
- **Event log:** ordered record of every agent action, used for visualization and analysis.
- **Quantization:** compressing a model to use less memory, for example 4-bit.
