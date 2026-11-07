"""
Agent - Autonomous Worker Loop for Decentralized Swarm (Stage 2).
Implements Non-Negotiable Rules:
- No central controller (agents self-coordinate via blackboard and stigmergic signals)
- Qwen 3.5 in every agent with role system prompts from runtime.roles
- Strict JSON actions validated against Pydantic schema
- Atomic task claims with leases
- Automatic QA and correction loop with fix_applied and test_failed tracking
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from runtime.blackboard import Blackboard, Task
from runtime.events import EventLog
from runtime.llm import ActionPayload, InitialTasksPayload, QwenClient
from runtime.qa import run_qa_audit
from runtime.roles import SwarmRole, get_role_by_hint
from runtime.sandbox import Sandbox
from runtime.tools import write_file

logger = logging.getLogger("runtime.agent")


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
        system_prompt: Optional[str] = None
    ):
        self.agent_id = agent_id
        self.role = role
        self.run_id = run_id
        self.blackboard = blackboard
        self.event_log = event_log
        self.sandbox = sandbox
        self.llm = llm_client

        # Resolve role configuration
        role_obj: Optional[SwarmRole] = get_role_by_hint(role)
        self.role_hint = role_obj.role_hint if role_obj else role.lower()
        self.system_prompt = system_prompt or (role_obj.system_prompt if role_obj else "")
        self.target_files = role_obj.target_files if role_obj else ["index.html"]
        self.sensitive_signals = role_obj.sensitive_signals if role_obj else []
        self.current_task: Optional[Task] = None

        # Log agent spawned event
        self.event_log.append(
            run_id=self.run_id,
            agent_id=self.agent_id,
            event_type="agent_spawned",
            target="",
            payload={"role": self.role, "role_hint": self.role_hint}
        )

    async def seed_initial_tasks(self, prompt: str) -> List[Task]:
        """
        One-time peer seeding: Coordinator or ordinary agent splits the prompt into initial tasks.
        Holds no ongoing command authority.
        """
        logger.info(f"Agent '{self.agent_id}' seeding initial role-specialized tasks...")
        user_prompt = f"""
Goal prompt: "{prompt}"

You are decomposing this goal into 4 specialized initial tasks:
1. "task-01-structure": HTML Document Structure in index.html (role_hint: "structure", priority: 5, target: "index.html"). Complete layout, semantic sections, CSS and JS links.
2. "task-02-styling": Modern Dark Theme CSS in styles.css (role_hint: "style", priority: 4, target: "styles.css"). Custom properties, responsive grid/flexbox, card styles, and animations.
3. "task-03-script": Client-Side Interactivity in script.js (role_hint: "script", priority: 3, target: "script.js"). Mobile navigation toggle, smooth scroll behavior, card hover/active interactions.
4. "task-04-qa": Automated Quality Assurance and Asset Audit (role_hint: "qa", priority: 1, target: "all"). Verify all assets, link integrity, and DOM selector consistency.

Return a JSON object with a list of tasks matching the InitialTasksPayload schema.
"""
        initial_data = await self.llm.generate_structured(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            schema=InitialTasksPayload
        )

        created_tasks = []
        for i, t_dict in enumerate(initial_data.tasks):
            t = Task(
                id=t_dict.get("id", f"task-0{i+1}"),
                run_id=self.run_id,
                title=t_dict.get("title", f"Task {i+1}"),
                description=t_dict.get("description", ""),
                role_hint=t_dict.get("role_hint", "structure"),
                status="open",
                priority=t_dict.get("priority", 1),
                target=t_dict.get("target", "index.html")
            )
            self.blackboard.add_task(t)
            created_tasks.append(t)
            logger.info(f"Seeded task: {t.id} - {t.title} (role_hint: {t.role_hint})")

        return created_tasks

    async def _step_qa(self) -> bool:
        """
        Specialized step for QA/Critic agent.
        Runs deterministic QA audits, creates correction tasks on failure, and validates fixes.
        """
        # Wait if generation tasks (structure, style, script) are still actively open or in progress
        all_tasks = self.blackboard.list_tasks(self.run_id)
        active_gen_tasks = [
            t for t in all_tasks
            if t.role_hint in ("structure", "style", "script")
            and not t.id.startswith("fix-")
            and t.status in ("open", "in_progress", "claimed")
        ]
        if active_gen_tasks:
            return False

        # Check if there are active fix tasks still open or in progress
        open_fixes = [t for t in all_tasks if t.id.startswith("fix-") and t.status in ("open", "in_progress", "claimed")]
        if open_fixes:
            # Wait for specialist agents to complete open fix tasks first
            return False

        # Check if QA task exists or need_qa signal is active
        open_qa_tasks = self.blackboard.list_tasks(self.run_id, status="open", role_hint="qa")
        active_signals = self.blackboard.get_active_signals(self.run_id)
        need_qa_signals = [s for s in active_signals if s.type == "need_qa"]

        if not open_qa_tasks and not need_qa_signals:
            return False

        # If a QA task exists, claim it
        claimed_task: Optional[Task] = None
        if open_qa_tasks:
            target_task = open_qa_tasks[0]
            if self.blackboard.claim_task_atomic(self.run_id, target_task.id, self.agent_id, lease_duration_sec=120.0):
                claimed_task = target_task
                self.blackboard.update_task_status(self.run_id, claimed_task.id, self.agent_id, "in_progress")

        # Execute QA audit
        report = run_qa_audit(self.sandbox)
        critical_or_high_defects = [d for d in report.defects if d.severity in ("critical", "high")]

        if critical_or_high_defects:
            # Defect found: Log test_failed event and spawn correction tasks
            logger.warning(f"QA Audit detected {len(critical_or_high_defects)} actionable defects in run '{self.run_id}'")
            self.event_log.append(
                run_id=self.run_id,
                agent_id=self.agent_id,
                event_type="test_failed",
                target="sandbox",
                payload={
                    "defects_count": len(critical_or_high_defects),
                    "defects": [{"target": d.target, "summary": d.summary, "role": d.role_hint} for d in critical_or_high_defects]
                }
            )

            # Group defects by target file so each file gets 1 consolidated fix task
            defects_by_target: Dict[str, List[QADefect]] = {}
            for d in critical_or_high_defects:
                defects_by_target.setdefault(d.target, []).append(d)

            for target_file, file_defects in defects_by_target.items():
                primary_role = file_defects[0].role_hint
                combined_summaries = "; ".join(d.summary for d in file_defects)
                combined_remediations = "\n".join(f"- {d.remediation}" for d in file_defects)

                fix_id = f"fix-{target_file.replace('.', '-')}-{int(time.time() * 1000) % 10000}"
                fix_task = Task(
                    id=fix_id,
                    run_id=self.run_id,
                    title=f"Fix {target_file}: {combined_summaries}",
                    description=f"Automated QA Failure on {target_file}:\n{combined_remediations}\nYou must output the complete updated file.",
                    role_hint=primary_role,
                    status="open",
                    priority=10,  # Highest priority to supersede ordinary tasks
                    target=target_file
                )
                self.blackboard.add_task(fix_task)
                self.blackboard.emit_signal(self.run_id, "bug_found", target_file, self.agent_id, initial_strength=2.0)
                logger.info(f"QA spawned consolidated correction task '{fix_task.id}' for role '{fix_task.role_hint}'")

            # If a QA task was claimed, reset it back to 'open' so QA re-verifies once fixes are applied
            if claimed_task:
                self.blackboard.update_task_status(self.run_id, claimed_task.id, None, "open")

            # Consume processed need_qa signals
            self.blackboard.consume_signal(self.run_id, "need_qa")
            return True

        else:
            # QA Passed
            logger.info(f"QA Audit PASSED for run '{self.run_id}' (Score: {report.score})")
            self.event_log.append(
                run_id=self.run_id,
                agent_id=self.agent_id,
                event_type="test_run",
                target="sandbox",
                payload={"status": "pass", "score": report.score, "checks": report.checks_passed}
            )

            self.blackboard.emit_signal(self.run_id, "qa_passed", "index.html", self.agent_id)
            self.blackboard.consume_signal(self.run_id, "need_qa")

            if claimed_task:
                self.blackboard.update_task_status(self.run_id, claimed_task.id, self.agent_id, "done")
                self.event_log.append(
                    run_id=self.run_id,
                    agent_id=self.agent_id,
                    event_type="task_done",
                    target="qa",
                    payload={"task_id": claimed_task.id, "score": report.score}
                )
            return True

    async def step(self) -> bool:
        """
        Single Observe-Decide-Act-Report cycle for a specialized swarm agent.
        Returns True if an action was performed, False if idle.
        """
        # Special branch for QA agent
        if self.role_hint == "qa":
            return await self._step_qa()

        # 1. OBSERVE: Reopen expired leases
        self.blackboard.reopen_expired_leases(self.run_id)

        # Check for open tasks matching this agent's role hint (or open to any)
        open_tasks = self.blackboard.list_tasks(self.run_id, status="open", role_hint=self.role_hint)

        if not open_tasks:
            # If no tasks at all for this run, coordinator seeds (or structure fallback if running solo)
            all_tasks = self.blackboard.list_tasks(self.run_id)
            if not all_tasks and self.role_hint == "integration":
                goal_data = self.blackboard.get_goal(self.run_id)
                prompt = goal_data.get("prompt", "") if goal_data else "Build a modern responsive landing page"
                await self.seed_initial_tasks(prompt)
                open_tasks = self.blackboard.list_tasks(self.run_id, status="open", role_hint=self.role_hint)
            elif not all_tasks and self.role_hint == "structure":
                await asyncio.sleep(0.5)
                all_tasks = self.blackboard.list_tasks(self.run_id)
                if not all_tasks:
                    goal_data = self.blackboard.get_goal(self.run_id)
                    prompt = goal_data.get("prompt", "") if goal_data else "Build a modern responsive landing page"
                    await self.seed_initial_tasks(prompt)
                    open_tasks = self.blackboard.list_tasks(self.run_id, status="open", role_hint=self.role_hint)

            if not open_tasks:
                # Check for active signals that might wake this agent to create a task
                active_signals = self.blackboard.get_active_signals(self.run_id)
                for sig in active_signals:
                    if sig.type in self.sensitive_signals:
                        # Stigmergic reaction: synthesize task from signal
                        sig_task_id = f"task-{sig.type.replace('_', '-')}-{int(time.time() * 1000) % 10000}"
                        t = Task(
                            id=sig_task_id,
                            run_id=self.run_id,
                            title=f"Reaction to {sig.type} on {sig.target}",
                            description=f"Triggered by signal '{sig.type}' with strength {sig.strength} on {sig.target}.",
                            role_hint=self.role_hint,
                            status="open",
                            priority=3,
                            target=sig.target
                        )
                        self.blackboard.add_task(t)
                        self.blackboard.consume_signal(self.run_id, sig.type, sig.target)
                        open_tasks = [t]
                        break

            if not open_tasks:
                return False

        # Pick the highest priority task (fix-* tasks have priority 10)
        target_task = open_tasks[0]

        # 2. DECIDE: Attempt atomic claim
        claimed = self.blackboard.claim_task_atomic(
            run_id=self.run_id,
            task_id=target_task.id,
            agent_id=self.agent_id,
            lease_duration_sec=300.0
        )

        if not claimed:
            logger.debug(f"Agent '{self.agent_id}': Task '{target_task.id}' claimed by peer.")
            return True

        self.current_task = target_task
        self.blackboard.update_task_status(self.run_id, target_task.id, self.agent_id, "in_progress")

        self.event_log.append(
            run_id=self.run_id,
            agent_id=self.agent_id,
            event_type="task_claimed",
            target=target_task.target,
            payload={"task_id": target_task.id, "title": target_task.title, "role": self.role}
        )

        # 3. ACT: Generate action via Qwen 3.5
        existing_files = self.sandbox.list_files()
        target_file = target_task.target.split(",")[0].strip() if target_task.target else "index.html"
        current_content = ""
        if self.sandbox.file_exists(target_file):
            current_content = f"\nExisting content of '{target_file}':\n```\n{self.sandbox.read_file(target_file)}\n```\n"

        # Also supply index.html context to style and script agents so they match DOM selectors
        context_files = ""
        if target_file != "index.html" and self.sandbox.file_exists("index.html"):
            context_files = f"\nReference 'index.html' (match your selectors to this markup):\n```\n{self.sandbox.read_file('index.html')}\n```\n"

        user_prompt = f"""
Current Task: {target_task.title}
Task ID: {target_task.id}
Description: {target_task.description}
Target File: {target_file}
Existing files in workspace: {existing_files}
{current_content}
{context_files}

Decide your action:
- To write or update code, return action "write_file" with args: {{"path": "{target_file}", "content": "<COMPLETE FULL UPDATED CODE>"}}.
- Include any appropriate signals in the "signals" field (e.g. 'need_styling', 'need_script', 'need_qa', 'need_integration').
- Provide a concise reasoning_summary.
"""
        try:
            action_data: ActionPayload = await self.llm.generate_structured(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                schema=ActionPayload
            )

            # Execute write_file action
            if action_data.action == "write_file":
                file_path = action_data.args.get("path", target_task.target or "index.html")
                file_content = action_data.args.get("content", "")

                write_res = write_file(self.sandbox, file_path, file_content)

                # Record artifact with optimistic versioning
                self.blackboard.record_artifact(
                    run_id=self.run_id,
                    path=file_path,
                    content_hash=write_res["content_hash"],
                    author_agent=self.agent_id
                )

                # Log file_edit or fix_applied event
                if target_task.id.startswith("fix-"):
                    self.event_log.append(
                        run_id=self.run_id,
                        agent_id=self.agent_id,
                        event_type="fix_applied",
                        target=file_path,
                        payload={"task_id": target_task.id, "summary": action_data.reasoning_summary, "bytes": write_res["bytes"]}
                    )
                else:
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

                # Automatic stigmergic handoffs
                if target_task.id.startswith("fix-"):
                    self.blackboard.emit_signal(self.run_id, "need_qa", file_path, self.agent_id)
                elif file_path == "index.html":
                    self.blackboard.emit_signal(self.run_id, "need_styling", "styles.css", self.agent_id)
                    self.blackboard.emit_signal(self.run_id, "need_script", "script.js", self.agent_id)
                elif file_path in ("styles.css", "script.js"):
                    self.blackboard.emit_signal(self.run_id, "need_qa", file_path, self.agent_id)

            elif action_data.action == "task_done":
                self.blackboard.update_task_status(self.run_id, target_task.id, self.agent_id, "done")
                self.event_log.append(
                    run_id=self.run_id,
                    agent_id=self.agent_id,
                    event_type="task_done",
                    target=target_task.target,
                    payload={"task_id": target_task.id}
                )

            # Emit any custom signals declared by LLM
            for sig in action_data.signals:
                s_type = sig.get("type", "need_qa")
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
