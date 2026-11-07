"""
Stage 1 Runner: Single Qwen 3.5 Agent Full Loop Execution.
Executes:
1. Initialize Blackboard, EventLog, Sandbox, and QwenClient
2. Set Goal on Blackboard
3. One-time seeding by ordinary agent into initial tasks
4. Agent claims tasks atomically and builds a complete single-page website
5. Verifies web assets in sandbox
6. Exports append-only events.jsonl trace to runs/<run_id>/
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime.blackboard import Blackboard
from runtime.events import EventLog
from runtime.llm import QwenClient
from runtime.sandbox import Sandbox
from runtime.agent import SwarmAgent
from runtime.tools import verify_web_assets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_stage1")


async def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else (
        "Build a modern responsive personal portfolio landing page for Alex Morgan, "
        "a Senior Full Stack Developer. Include a clean navbar, hero section with call-to-action, "
        "skills showcase (React, Python, Node, Docker), featured projects grid with preview cards, "
        "and a contact footer with social links. Use clean modern CSS with dark theme aesthetics."
    )
    model_name = sys.argv[2] if len(sys.argv) > 2 else os.getenv("DEFAULT_MODEL", "qwen3.5:4b")

    run_id = f"run_{int(time.time())}"
    runs_dir = Path("runs") / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("STAGE 1: SWARM WEBSITE BUILDER - SINGLE QWEN AGENT LOOP")
    print(f"Run ID    : {run_id}")
    print(f"Model     : {model_name}")
    print(f"Prompt    : {prompt}")
    print("=" * 70)

    # 1. Initialize Subsystems
    db_path = str(runs_dir / "blackboard.db")
    blackboard = Blackboard(db_path=db_path)
    event_log = EventLog(db_path=db_path)
    sandbox = Sandbox(run_id=run_id, base_dir=".sandbox")
    llm_client = QwenClient(model=model_name)

    # 2. Record Goal on Blackboard
    blackboard.set_goal(run_id=run_id, prompt=prompt)
    logger.info("Goal recorded on blackboard.")

    # 3. Spawn Single Agent (Frontend role)
    agent = SwarmAgent(
        agent_id="agent-frontend-01",
        role="Frontend",
        run_id=run_id,
        blackboard=blackboard,
        event_log=event_log,
        sandbox=sandbox,
        llm_client=llm_client
    )

    # 4. Execute Full Agent Loop
    max_steps = 10
    step_count = 0
    t_start = time.time()

    while step_count < max_steps:
        step_count += 1
        logger.info(f"--- Agent Step {step_count}/{max_steps} ---")
        has_more = await agent.step()
        if not has_more:
            logger.info("Agent completed all available tasks.")
            break

    total_time = round(time.time() - t_start, 2)

    # 5. Verify Sandbox Output
    verification = verify_web_assets(sandbox)
    generated_files = sandbox.list_files()

    # 6. Export Event Log Single Source of Truth
    jsonl_path = runs_dir / "events.jsonl"
    event_count = event_log.export_jsonl(run_id, str(jsonl_path))

    # 7. Final Summary & Deliverables
    print("\n" + "=" * 70)
    print("STAGE 1 EXECUTION DELIVERABLES SUMMARY:")
    print(f"  Total Duration       : {total_time}s")
    print(f"  Steps Completed      : {step_count}")
    print(f"  Generated Files      : {generated_files}")
    print(f"  Sandbox Directory    : {sandbox.sandbox_dir}")
    print(f"  Verification Result  : {'PASS' if verification['valid'] else 'FAIL'}")
    if verification["issues"]:
        print(f"  Verification Issues  : {verification['issues']}")
    print(f"  Events Logged        : {event_count} events written to {jsonl_path}")
    print("=" * 70)

    if not verification["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
