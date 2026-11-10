"""
Swarm - Asynchronous Decentralized Multi-Agent Swarm (Stage 2).
Coordinates concurrent execution of 5 specialized agents:
- Structure Specialist (HTML5)
- Style Specialist (CSS)
- Script Specialist (JS)
- QA / Critic Specialist (Defect Detection & Remediation)
- Integration / Coordinator Specialist (Peer Decomposer & Cross-Asset Cohesion)

Guarantees:
- Asynchronous worker execution via asyncio.gather()
- Single GPU semaphore serialization protecting laptop GPU VRAM
- Pure blackboard coordination with stigmergic signals (no central command controller)
- Automated QA and correction loop
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from runtime.agent import SwarmAgent
from runtime.blackboard import Blackboard
from runtime.events import EventLog
from runtime.llm import QwenClient
from runtime.qa import run_qa_audit
from runtime.roles import (
    ROLE_STRUCTURE,
    ROLE_STYLE,
    ROLE_SCRIPT,
    ROLE_QA,
    ROLE_COORDINATOR
)
from runtime.sandbox import Sandbox
from runtime.vision.feedback import VisionFeedbackLoop
from runtime.vision.similarity import VisualDiffResult

logger = logging.getLogger("runtime.swarm")


class Swarm:
    def __init__(
        self,
        run_id: str,
        goal_prompt: str,
        blackboard: Blackboard,
        event_log: EventLog,
        sandbox: Sandbox,
        llm_client: QwenClient,
        reference_image: Optional[str] = None,
        vision_loop: Optional[VisionFeedbackLoop] = None,
    ):
        self.run_id = run_id
        self.goal_prompt = goal_prompt
        self.reference_image = reference_image
        self.vision_loop = vision_loop
        self.blackboard = blackboard
        self.event_log = event_log
        self.sandbox = sandbox
        self.llm_client = llm_client

        # Record goal on blackboard
        self.blackboard.set_goal(self.run_id, self.goal_prompt, reference_image=self.reference_image)

        # Initialize the 5 specialized peer agents
        self.agents: List[SwarmAgent] = [
            SwarmAgent(
                agent_id=ROLE_COORDINATOR.default_agent_id,
                role=ROLE_COORDINATOR.name,
                run_id=self.run_id,
                blackboard=self.blackboard,
                event_log=self.event_log,
                sandbox=self.sandbox,
                llm_client=self.llm_client,
                system_prompt=ROLE_COORDINATOR.system_prompt
            ),
            SwarmAgent(
                agent_id=ROLE_STRUCTURE.default_agent_id,
                role=ROLE_STRUCTURE.name,
                run_id=self.run_id,
                blackboard=self.blackboard,
                event_log=self.event_log,
                sandbox=self.sandbox,
                llm_client=self.llm_client,
                system_prompt=ROLE_STRUCTURE.system_prompt
            ),
            SwarmAgent(
                agent_id=ROLE_STYLE.default_agent_id,
                role=ROLE_STYLE.name,
                run_id=self.run_id,
                blackboard=self.blackboard,
                event_log=self.event_log,
                sandbox=self.sandbox,
                llm_client=self.llm_client,
                system_prompt=ROLE_STYLE.system_prompt
            ),
            SwarmAgent(
                agent_id=ROLE_SCRIPT.default_agent_id,
                role=ROLE_SCRIPT.name,
                run_id=self.run_id,
                blackboard=self.blackboard,
                event_log=self.event_log,
                sandbox=self.sandbox,
                llm_client=self.llm_client,
                system_prompt=ROLE_SCRIPT.system_prompt
            ),
            SwarmAgent(
                agent_id=ROLE_QA.default_agent_id,
                role=ROLE_QA.name,
                run_id=self.run_id,
                blackboard=self.blackboard,
                event_log=self.event_log,
                sandbox=self.sandbox,
                llm_client=self.llm_client,
                system_prompt=ROLE_QA.system_prompt
            ),
        ]

    async def _worker_loop(self, agent: SwarmAgent, stop_event: asyncio.Event):
        """Asynchronous execution loop for an individual swarm peer."""
        logger.info(f"Agent worker '{agent.agent_id}' ({agent.role_hint}) started.")
        while not stop_event.is_set():
            try:
                acted = await agent.step()
                if acted:
                    # Yield control to event loop so other agents can step
                    await asyncio.sleep(0.05)
                else:
                    # Idle: wait for blackboard signals or open tasks
                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unhandled error in agent '{agent.agent_id}': {e}", exc_info=True)
                await asyncio.sleep(1.0)
        logger.info(f"Agent worker '{agent.agent_id}' stopped.")

    async def run(self, max_seconds: float = 900.0, poll_interval: float = 1.0) -> Dict[str, Any]:
        """
        Run all 5 agents concurrently until convergence or timeout.
        Decentralized termination: Monitors blackboard status for completion and QA verification.
        """
        stop_event = asyncio.Event()
        start_time = time.time()

        # Launch all 5 agent worker loops concurrently
        tasks = [
            asyncio.create_task(self._worker_loop(agent, stop_event))
            for agent in self.agents
        ]

        logger.info(f"Swarm '{self.run_id}' started with {len(self.agents)} concurrent specialized agents.")

        converged = False
        qa_report = None
        vision_iter = 1

        try:
            while time.time() - start_time < max_seconds:
                await asyncio.sleep(poll_interval)

                # Check if all tasks are done and minimum initial tasks exist
                if self.blackboard.is_swarm_converged(self.run_id):
                    # Verify QA status
                    qa_report = run_qa_audit(self.sandbox)
                    active_signals = self.blackboard.get_active_signals(self.run_id)
                    pending_bugs = [s for s in active_signals if s.type in ("bug_found", "need_qa", "need_styling", "need_script")]

                    if qa_report.passed and not pending_bugs:
                        # If a reference image is provided, evaluate visual convergence
                        if self.reference_image and self.vision_loop:
                            vision_result = self.vision_loop.run_iteration(
                                run_id=self.run_id,
                                blackboard=self.blackboard,
                                event_log=self.event_log,
                                sandbox=self.sandbox,
                                reference_image_path=self.reference_image,
                                iteration=vision_iter,
                            )
                            if vision_result.converged:
                                logger.info(
                                    f"Vision loop converged with score {vision_result.composite_score:.2f} "
                                    f"(threshold {vision_result.threshold}). Swarm converged."
                                )
                                converged = True
                                break
                            else:
                                vision_iter += 1
                                if vision_iter > self.vision_loop.max_iterations:
                                    logger.info(
                                        f"Maximum vision iterations ({self.vision_loop.max_iterations}) reached. "
                                        f"Concluding with score {vision_result.composite_score:.2f}."
                                    )
                                    converged = True
                                    break
                                logger.info(
                                    f"Vision iteration {vision_iter - 1} generated targeted repair tasks. "
                                    f"Continuing swarm loop."
                                )
                                continue

                        logger.info("All tasks completed and QA audit passed cleanly. Swarm converged.")
                        converged = True
                        break
                    else:
                        all_tasks_now = self.blackboard.list_tasks(self.run_id)
                        prior_fix_tasks = [t for t in all_tasks_now if t.id.startswith("fix-")]
                        if len(prior_fix_tasks) >= 3 and not pending_bugs:
                            logger.info(f"Maximum 3 repair cycles reached for '{self.run_id}'. Concluding run honestly with partial status.")
                            break
                        logger.debug("Tasks finished but QA detected issues or pending signals. Continuing loop.")

        finally:
            stop_event.set()
            # Cancel all worker coroutines
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = round(time.time() - start_time, 2)
        if not qa_report:
            qa_report = run_qa_audit(self.sandbox)

        all_tasks = self.blackboard.list_tasks(self.run_id)
        done_tasks = [t for t in all_tasks if t.status == "done"]

        return {
            "run_id": self.run_id,
            "converged": converged,
            "status": "converged" if converged else ("partial" if len(done_tasks) >= 4 else "failed"),
            "elapsed_seconds": elapsed,
            "total_tasks": len(all_tasks),
            "completed_tasks": len(done_tasks),
            "qa_passed": qa_report.passed,
            "qa_score": qa_report.score,
            "coverage_percent": qa_report.coverage_percent,
            "qa_defects": [d.__dict__ for d in qa_report.defects],
            "sandbox_files": self.sandbox.list_files()
        }
