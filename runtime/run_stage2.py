"""
Stage 2 Execution Script: Autonomous Multi-Agent Swarm with Qwen 3.5.
Launches 5 concurrent specialized agents:
- agent-coordinator-01 (Integration Coordinator)
- agent-structure-01 (HTML5 Specialist)
- agent-style-01 (CSS Styling Specialist)
- agent-script-01 (JavaScript Specialist)
- agent-qa-01 (Automated QA & Correction Specialist)

Executes with GPU semaphore (concurrency = 1) protecting laptop RTX 4050.
Logs complete transactional event trace to runs/<run_id>/events.jsonl.
"""

import argparse
import asyncio
import logging
import os
from pathlib import Path
import sys
import time

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from runtime.blackboard import Blackboard
from runtime.events import EventLog
from runtime.llm import QwenClient
from runtime.qa import run_qa_audit
from runtime.sandbox import Sandbox
from runtime.swarm import Swarm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("stage2")

DEFAULT_PROMPT = (
    "Build a modern responsive landing page for 'NexusAI' - an autonomous multi-agent swarm platform. "
    "Include a futuristic dark navbar with logo and links, a hero section with high-impact badge and call-to-action buttons, "
    "a 4-column feature grid showing swarm capabilities (Decentralized, Self-Healing, Reactive Pheromones, Zero-Config), "
    "an interactive metrics/preview section, and a clean contact footer with status indicators. "
    "Use clean modern CSS with dark aesthetics, glassmorphism cards, purple/indigo gradients, and responsive mobile navigation."
)


async def main():
    parser = argparse.ArgumentParser(description="Run Stage 2 Decentralized Multi-Agent Swarm")
    parser.add_argument("--prompt", type=str, default=DEFAULT_PROMPT, help="Website generation goal prompt")
    parser.add_argument("--model", type=str, default="qwen3.5:4b", help="Ollama model tag")
    parser.add_argument("--max-seconds", type=float, default=1200.0, help="Maximum timeout in seconds")
    args = parser.parse_args()

    run_id = f"run_{int(time.time())}"
    run_dir = REPO_ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    db_path = str(run_dir / "blackboard.db")
    sandbox_base = str(REPO_ROOT / ".sandbox")

    print("=" * 70)
    print("STAGE 2: DECENTRALIZED MULTI-AGENT SWARM EXECUTION")
    print(f"Run ID    : {run_id}")
    print(f"Model     : {args.model} (Serialized via GPU Semaphore)")
    print("Agents    : 5 Specialized Workers (Coordinator, Structure, Style, Script, QA)")
    print(f"Prompt    : {args.prompt[:120]}...")
    print("=" * 70)

    # Initialize components
    blackboard = Blackboard(db_path)
    event_log = EventLog(db_path)
    sandbox = Sandbox(run_id=run_id, base_dir=sandbox_base)
    llm_client = QwenClient(model=args.model)

    # Initialize multi-agent swarm
    swarm = Swarm(
        run_id=run_id,
        goal_prompt=args.prompt,
        blackboard=blackboard,
        event_log=event_log,
        sandbox=sandbox,
        llm_client=llm_client
    )

    t0 = time.time()
    result = await swarm.run(max_seconds=args.max_seconds, poll_interval=1.0)
    total_duration = round(time.time() - t0, 2)

    # Export event log to JSONL
    jsonl_path = run_dir / "events.jsonl"
    exported_count = event_log.export_jsonl(run_id, str(jsonl_path))

    # Run final QA verification
    qa_report = run_qa_audit(sandbox)
    generated_files = sandbox.list_files()

    print("\n" + "=" * 70)
    print("STAGE 2 EXECUTION DELIVERABLES SUMMARY:")
    print(f"  Total Duration       : {total_duration}s")
    print(f"  Swarm Converged      : {result['converged']}")
    print(f"  Total Tasks          : {result['total_tasks']} (Completed: {result['completed_tasks']})")
    print(f"  QA Score             : {qa_report.score}/100.0 (Passed: {qa_report.passed})")
    print(f"  Generated Files      : {generated_files}")
    print(f"  Sandbox Directory    : {sandbox.root}")
    print(f"  Events Logged        : {exported_count} events written to {jsonl_path}")
    print("=" * 70)

    if not qa_report.passed:
        print("\nQA Defect Warnings:")
        for d in qa_report.defects:
            print(f"  - [{d.severity.upper()}] {d.target}: {d.summary}")
    else:
        print("\nQA Verification Details:")
        for check in qa_report.checks_passed:
            print(f"  [x] {check}")


if __name__ == "__main__":
    asyncio.run(main())

