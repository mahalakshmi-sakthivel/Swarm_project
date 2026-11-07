"""
Agent - Autonomous Worker Loop powered by Qwen 3.5.
Implements Non-Negotiable Rules:
- No central controller (agents self-coordinate via blackboard)
- Qwen 3.5 in every agent with role system prompts
- Strict JSON actions validated against Pydantic schema
- Atomic task claims with leases
- Single-page website generation for Stage 1
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from runtime.blackboard import Blackboard, Task
from runtime.events import EventLog
from runtime.llm import ActionPayload, InitialTasksPayload, QwenClient
from runtime.sandbox import Sandbox
from runtime.tools import write_file, verify_web_assets

logger = logging.getLogger("runtime.agent")

DEFAULT_SYSTEM_PROMPT = """
You are an autonomous AI software engineer in a decentralized swarm.
You work independently without a central manager, taking tasks from a shared blackboard.
Always produce clean, modern, responsive HTML, CSS, and vanilla JavaScript.
You must return only strict JSON matching the requested action schema.

CRITICAL CODE COMPLETION RULE:
When performing a 'write_file' action on any file (especially HTML, CSS, or JS), you MUST output the COMPLETE, full file content from start to finish. Never return snippets, diffs, or isolated fragments. For HTML files, always provide a complete document with <!DOCTYPE html>, <html>, <head>, <body>, all existing sections, and </html>.
"""


class SwarmAgent:
    def __init__(
        self,
        agent_id: str,
        role: str,
        run_id: str,
        blackboard: Blackboard,
        event_log: EventLog,
        sandbox: Sandbox,
        llm_client: QwenClient,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT
    ):
        self.agent_id = agent_id
        self.role = role
        self.run_id = run_id
        self.blackboard = blackboard
        self.event_log = event_log
        self.sandbox = sandbox
        self.llm = llm_client
        self.system_prompt = system_prompt
        self.current_task: Optional[Task] = None

        # Log agent spawned event
        self.event_log.append(
            run_id=self.run_id,
            agent_id=self.agent_id,
            event_type="agent_spawned",
            target="",
            payload={"role": self.role}
        )

    async def seed_initial_tasks(self, prompt: str) -> List[Task]:
        """
        One-time seeding step: An ordinary agent splits the prompt into initial tasks.
        Holds no ongoing authority.
        """
        logger.info(f"Agent '{self.agent_id}' seeding initial tasks for goal...")
        user_prompt = f"""
Goal prompt: "{prompt}"

You are breaking this goal down into 2 to 3 initial concrete tasks for a single-page website:
1. "task-01-structure": Complete HTML document structure with all semantic sections in index.html (navbar, hero with CTA, skills showcase, projects cards, contact footer).
2. "task-02-styling": Comprehensive modern responsive dark-theme CSS in styles.css.
3. "task-03-script": Interactive vanilla JavaScript in script.js (mobile navigation toggle, smooth scroll).

Return a JSON object with a list of tasks.
Each task must have:
- "id": a unique slug, e.g. "task-01-structure"
- "title": short title
- "description": specific instructions for building the file or component
- "role_hint": target role (e.g. "Frontend")
- "target": target file (e.g. "index.html", "styles.css", or "script.js")
- "priority": integer 1 to 5 (5 highest)
"""
        initial_data = await self.llm.generate_structured(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            schema=InitialTasksPayload
        )

        created_tasks = []
        for i, t_dict in enumerate(initial_data.tasks):
            t = Task(
                id=t_dict.get("id", f"task-{i+1}"),
                run_id=self.run_id,
                title=t_dict.get("title", f"Task {i+1}"),
                description=t_dict.get("description", ""),
                role_hint=t_dict.get("role_hint", self.role),
                status="open",
                priority=t_dict.get("priority", 1),
                target=t_dict.get("target", "index.html")
            )
            self.blackboard.add_task(t)
            created_tasks.append(t)
            logger.info(f"Seeded task: {t.id} - {t.title}")

        return created_tasks

    async def step(self) -> bool:
        """
        Single Observe-Decide-Act-Report cycle.
        Returns True if an action was performed, False if no open tasks remain.
        """
        # 1. OBSERVE: Reopen any expired leases and check open tasks
        self.blackboard.reopen_expired_leases(self.run_id)
        open_tasks = self.blackboard.list_tasks(self.run_id, status="open")

        if not open_tasks:
            # Check if there are no tasks at all for this run (need seeding)
            all_tasks = self.blackboard.list_tasks(self.run_id)
            if not all_tasks:
                goal_data = self.blackboard.get_goal(self.run_id)
                prompt = goal_data.get("prompt", "") if goal_data else "Build a modern landing page"
                await self.seed_initial_tasks(prompt)
                open_tasks = self.blackboard.list_tasks(self.run_id, status="open")
            
            if not open_tasks:
                logger.info(f"Agent '{self.agent_id}': No open tasks remaining.")
                return False

        # Pick the highest priority task
        target_task = open_tasks[0]

        # 2. DECIDE: Attempt atomic claim
        claimed = self.blackboard.claim_task_atomic(
            run_id=self.run_id,
            task_id=target_task.id,
            agent_id=self.agent_id,
            lease_duration_sec=300.0
        )

        if not claimed:
            logger.info(f"Agent '{self.agent_id}': Task '{target_task.id}' was claimed by another agent.")
            return True

        self.current_task = target_task
        self.blackboard.update_task_status(self.run_id, target_task.id, self.agent_id, "in_progress")

        self.event_log.append(
            run_id=self.run_id,
            agent_id=self.agent_id,
            event_type="task_claimed",
            target=target_task.target,
            payload={"task_id": target_task.id, "title": target_task.title}
        )

        # 3. ACT: Generate action via Qwen 3.5
        existing_files = self.sandbox.list_files()
        target_file = target_task.target.split(",")[0].strip() if target_task.target else "index.html"
        current_content = ""
        if self.sandbox.file_exists(target_file):
            current_content = f"\nExisting content of '{target_file}':\n```\n{self.sandbox.read_file(target_file)}\n```\n"

        user_prompt = f"""
Current Task: {target_task.title}
Description: {target_task.description}
Target File: {target_file}
Existing files in workspace: {existing_files}
{current_content}
Decide your action:
- If you need to create or update a file, return action "write_file" with args: {{"path": "{target_file}", "content": "<COMPLETE FULL UPDATED CODE>"}}.
- If the task is already satisfied by existing files, return action "task_done".
- Always provide reasoning_summary.
"""
        try:
            action_data: ActionPayload = await self.llm.generate_structured(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                schema=ActionPayload
            )

            # Execute action
            if action_data.action == "write_file":
                file_path = action_data.args.get("path", target_task.target or "index.html")
                file_content = action_data.args.get("content", "")

                write_res = write_file(self.sandbox, file_path, file_content)
                
                # Record artifact
                self.blackboard.record_artifact(
                    run_id=self.run_id,
                    path=file_path,
                    content_hash=write_res["content_hash"],
                    author_agent=self.agent_id
                )

                # Log file edit event
                self.event_log.append(
                    run_id=self.run_id,
                    agent_id=self.agent_id,
                    event_type="file_edit",
                    target=file_path,
                    payload={"bytes": write_res["bytes"], "summary": action_data.reasoning_summary}
                )

                # Mark task done
                self.blackboard.update_task_status(self.run_id, target_task.id, self.agent_id, "done")
                self.event_log.append(
                    run_id=self.run_id,
                    agent_id=self.agent_id,
                    event_type="task_done",
                    target=target_task.target,
                    payload={"task_id": target_task.id}
                )

            elif action_data.action == "task_done":
                self.blackboard.update_task_status(self.run_id, target_task.id, self.agent_id, "done")
                self.event_log.append(
                    run_id=self.run_id,
                    agent_id=self.agent_id,
                    event_type="task_done",
                    target=target_task.target,
                    payload={"task_id": target_task.id}
                )

            # Check signals to emit
            for sig in action_data.signals:
                s_type = sig.get("type", "needs_review")
                s_target = sig.get("target", target_task.target)
                self.blackboard.emit_signal(self.run_id, s_type, s_target, self.agent_id)
                self.event_log.append(
                    run_id=self.run_id,
                    agent_id=self.agent_id,
                    event_type="signal_emitted",
                    target=s_target,
                    payload={"type": s_type}
                )

        except Exception as e:
            logger.error(f"Task '{target_task.id}' failed in agent '{self.agent_id}': {e}")
            self.blackboard.update_task_status(self.run_id, target_task.id, self.agent_id, "failed")
            self.event_log.append(
                run_id=self.run_id,
                agent_id=self.agent_id,
                event_type="agent_failed",
                target=target_task.target,
                payload={"task_id": target_task.id, "error": str(e)}
            )

        self.current_task = None
        return True
