# Swarm Website Builder

> **Decentralized Multi-Agent Website Generation Powered by Qwen 3.5**

Swarm Website Builder is an experimental, decentralized multi-agent system where specialized AI agents collaborate without a central orchestrator to design, implement, test, and refine websites from natural-language prompts or reference screenshots.

---

## 1. Core Principles

- **No Central Controller:** Agents coordinate solely via stigmergy—reading and posting tasks, signals, artifacts, and scores to a shared blackboard.
- **Qwen 3.5 Inside Every Agent:** Every agent reasons with Qwen 3.5 (via Ollama) using structured JSON output schemas with automated retry logic.
- **Event Log Single Source of Truth:** Every action is recorded in an append-only SQLite event log.
- **Real-Time Cursor Visualization:** The live UI renders animated cursors mapped 1:1 to logged agent events (no decorative/fake animations).
- **Hardware-Aware & Safe:** Optimized for consumer laptops (e.g., RTX 4050 6GB VRAM) via 4-bit quantization, serialized inference queues, and isolated sandboxing.

---

## 2. Repository Layout

```
swarm-builder/
  README.md
  docs/                  # PRD, TRD, SRS, Stage notes
  runtime/
    blackboard.py        # Zones, atomic claims, leases, optimistic versioning
    events.py            # Append-only SQLite event schema
    agent.py             # Observe-Decide-Act-Report loop
    bidding.py           # Multi-factor bid scoring
    signals.py           # Pheromone-like signal decay and reinforcement
    llm.py               # Shared Qwen client with JSON schema validation
    tools.py             # Sandboxed file/test/screenshot tools
    sandbox.py           # Isolated workspace execution
    roles/               # Role prompts (UI/UX, Frontend, Backend, etc.)
  api/
    main.py              # FastAPI REST & WebSocket streaming server
  ui/                    # React dashboard & cursor replay engine
  eval/
    baselines/           # B1 (single-shot), B2 (test/fix loop), B3 (centralized)
    prompts/             # Benchmark test prompts
    screenshots/         # Benchmark reference images
    run_benchmark.py     # Evaluation harness
    metrics.py           # Lighthouse, test-pass, SSIM calculations
  tests/                 # Automated unit and integration test suite
  runs/                  # Run artifacts and events.jsonl traces
```

---

## 3. Quickstart (Development Setup)

### Prerequisites
- Windows 10/11 or Linux
- Python 3.11+
- Node.js v18+
- Ollama with Qwen 3.5 quantized models

### Installation
```bash
# Clone and enter directory
cd "d:/swarm technology"

# Activate Python Virtual Environment
.venv\Scripts\activate

# Install dependencies (managed in Stage 1)
pip install -r requirements.txt
```

---

## 4. Project Documentation
- [PRD (Product Requirements Document)](docs/PRD.md)
- [TRD (Technical Requirements Document)](docs/TRD.md)
- [SRS (Software Requirements Specification)](docs/SRS.md)
- [Architecture & System Design](docs/architecture.md)
- [Data Model & API Specification](docs/data_model_and_api.md)
- [UX / UI Specification](docs/ux_ui_spec.md)
- [Stage 0 Verification Notes](docs/stage-0.md)

---

## 5. Development Stages & Gates
- **Stage 0**: Setup, Hardware & Model Verification `[In Progress]`
- **Stage 1**: Blackboard + Single Qwen Agent `[Pending Approval]`
- **Stage 2**: Multi-Agent Swarm with Bidding & Leases `[Pending Approval]`
- **Stage 3**: Event Log Streaming & Cursor Visualization `[Pending Approval]`
- **Stage 4**: Testing Agent, Vision Loop & Screenshot Mode `[Pending Approval]`
- **Stage 5**: Failure Injection & Evaluation against Baselines `[Pending Approval]`
- **Stage 6**: Polish, Documentation & Scripted Demo `[Pending Approval]`

