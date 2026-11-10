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
from runtime.spec import SiteSpec, generate_default_spec, parse_or_repair_spec
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
        Instant deterministic peer seeding: Splits the goal prompt into structured tasks,
        starting with task-00-plan to synthesize the canonical SiteSpec contract (spec.json).
        """
        logger.info(f"Agent '{self.agent_id}' seeding initial role-specialized tasks for: '{prompt}'...")
        prompt_snippet = prompt[:60] + "..." if len(prompt) > 60 else prompt

        initial_tasks_def = [
            {
                "id": "task-00-plan",
                "title": f"Synthesize SiteSpec Contract (spec.json) for '{prompt_snippet}'",
                "description": (
                    f"Analyze user requirements for: '{prompt}'. "
                    f"Synthesize the canonical SiteSpec contract in spec.json detailing site_type, brand_name, "
                    f"tagline, audience, tone, pages hierarchy, nav order, theme color tokens, and concrete requirements checklist."
                ),
                "role_hint": "integration",
                "priority": 10,
                "target": "spec.json",
                "depends_on": []
            },
            {
                "id": "task-01-structure",
                "title": f"HTML5 Structure for '{prompt_snippet}'",
                "description": (
                    f"Create semantic inner <main> section content for index.html strictly following spec.json. "
                    f"Use ONLY standard design system component classes from base.css (.container, .section, .hero, .grid, .card, "
                    f".btn-primary, .btn-outline, .btn-accent, .badge, .form, .testimonial, .pricing, .gallery, .faq, .stats). "
                    f"Do NOT invent custom class names. <head>, <nav>, and <footer> are automatically rendered in Python."
                ),
                "role_hint": "structure",
                "priority": 5,
                "target": "index.html",
                "depends_on": ["task-00-plan"]
            },
            {
                "id": "task-02-styling",
                "title": "Page-Specific Styles & Visual Polish (styles.css)",
                "description": (
                    f"Write page-specific CSS extras, micro-animations, hero gradients, and card transitions in styles.css. "
                    f"base.css is ALREADY PROVIDED with :root variables and complete component library. "
                    f"DO NOT redefine :root variables and DO NOT duplicate base styles. "
                    f"DO NOT hard-code hex colors; always use theme CSS variables: var(--primary), var(--secondary), var(--accent), var(--bg-surface), etc."
                ),
                "role_hint": "style",
                "priority": 4,
                "target": "styles.css",
                "depends_on": ["task-00-plan", "task-01-structure"]
            },
            {
                "id": "task-03-script",
                "title": "Client-Side Functionality & Interactivity (script.js)",
                "description": (
                    f"Implement clean vanilla ES6+ JavaScript in script.js to power the interactive features required for: '{prompt}'. "
                    f"Provide dynamic functionality matching the elements present in index.html and features defined in spec.json (e.g., mobile navigation toggle, "
                    f"live calculations, data filtering, modal dialogs, smooth scrolling, tab switching, or simulated real-time updates). "
                    f"Wrap all DOM lookups with null checks so no runtime errors occur. Output full working JavaScript."
                ),
                "role_hint": "script",
                "priority": 3,
                "target": "script.js",
                "depends_on": ["task-00-plan", "task-01-structure"]
            },
            {
                "id": "task-04-qa",
                "title": "Automated Quality Assurance and Asset Audit",
                "description": "Deterministic validation of HTML, CSS, JS, and spec.json conformance. Verify links, selectors, and accessibility.",
                "role_hint": "qa",
                "priority": 1,
                "target": "all",
                "depends_on": ["task-00-plan", "task-01-structure", "task-02-styling", "task-03-script"]
            }
        ]

        created_tasks = []
        for t_dict in initial_tasks_def:
            t = Task(
                id=t_dict["id"],
                run_id=self.run_id,
                title=t_dict["title"],
                description=t_dict["description"],
                role_hint=t_dict["role_hint"],
                status="open",
                priority=t_dict["priority"],
                target=t_dict["target"],
                depends_on=t_dict["depends_on"]
            )
            self.blackboard.add_task(t)
            created_tasks.append(t)
            logger.info(f"Seeded task: {t.id} - {t.title} (role_hint: {t.role_hint}, depends_on: {t.depends_on})")

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
            # If no tasks at all for this run, attempt atomic seed lock claim
            all_tasks = self.blackboard.list_tasks(self.run_id)
            if not all_tasks and self.role_hint in ("integration", "structure"):
                if self.blackboard.claim_seed_lock(self.run_id, self.agent_id):
                    goal_data = self.blackboard.get_goal(self.run_id)
                    prompt = goal_data.get("prompt", "") if goal_data else "Build a modern responsive landing page"
                    await self.seed_initial_tasks(prompt)
                    open_tasks = self.blackboard.list_tasks(self.run_id, status="open", role_hint=self.role_hint)
                else:
                    # Another agent is currently seeding; wait for tasks to appear
                    return False

            if not open_tasks:
                # Check for active signals that might wake this agent to create a task
                active_signals = self.blackboard.get_active_signals(self.run_id)
                for sig in active_signals:
                    if sig.type in self.sensitive_signals:
                        # If target file already exists and this is not a bug repair signal, consume and skip
                        if sig.target and self.sandbox.file_exists(sig.target) and "bug" not in sig.type:
                            self.blackboard.consume_signal(self.run_id, sig.type, sig.target)
                            continue

                        # If an existing task for this target already exists or finished, consume and skip
                        target_tasks = [t for t in all_tasks if t.target == sig.target]
                        if target_tasks and "bug" not in sig.type:
                            self.blackboard.consume_signal(self.run_id, sig.type, sig.target)
                            continue

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

        # Filter for tasks whose dependencies are fully resolved
        all_tasks = self.blackboard.list_tasks(self.run_id)
        done_task_ids = {t.id for t in all_tasks if t.status in ("done", "completed")}

        ready_tasks = [
            t for t in open_tasks
            if all(dep in done_task_ids for dep in t.depends_on)
        ]

        if not ready_tasks:
            return False

        # Pick the highest priority ready task (fix-* tasks have priority 10)
        target_task = ready_tasks[0]

        # 2. DECIDE: Attempt atomic claim with safe 600s lease
        claimed = self.blackboard.claim_task_atomic(
            run_id=self.run_id,
            task_id=target_task.id,
            agent_id=self.agent_id,
            lease_duration_sec=600.0
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

        # Retrieve overarching user goal prompt from blackboard
        goal_data = self.blackboard.get_goal(self.run_id) or {}
        user_goal_prompt = goal_data.get("prompt", "")

        # 3. ACT: Handle task execution
        # Check if this is the architectural planning task (task-00-plan)
        if target_task.id == "task-00-plan":
            logger.info(f"Coordinator '{self.agent_id}' synthesizing SiteSpec contract for: '{user_goal_prompt}'...")
            spec = generate_default_spec(user_goal_prompt)
            spec_json = spec.model_dump_json(indent=2)
            write_res = write_file(self.sandbox, "spec.json", spec_json)

            self.blackboard.record_artifact(
                run_id=self.run_id,
                path="spec.json",
                content_hash=write_res["content_hash"],
                author_agent=self.agent_id
            )

            self.event_log.append(
                run_id=self.run_id,
                agent_id=self.agent_id,
                event_type="file_edit",
                target="spec.json",
                payload={"bytes": write_res["bytes"], "summary": f"Synthesized SiteSpec for {spec.brand_name} ({spec.site_type})"}
            )

            # Generate and record deterministic base.css component library (Phase 3)
            from runtime.theme import generate_base_css
            base_css_content = generate_base_css(spec.theme)
            base_res = self.sandbox.write_file("base.css", base_css_content)
            self.blackboard.record_artifact(
                run_id=self.run_id,
                path="base.css",
                content_hash=base_res["content_hash"],
                author_agent=self.agent_id
            )
            self.event_log.append(
                run_id=self.run_id,
                agent_id=self.agent_id,
                event_type="file_edit",
                target="base.css",
                payload={"bytes": base_res["bytes"], "summary": f"Generated base.css ({spec.theme.mood} theme) with complete component library"}
            )

            # Dynamically seed structure tasks for all pages in spec.pages
            structure_task_ids = []
            for idx, p in enumerate(spec.pages):
                t_id = "task-01-structure" if idx == 0 else f"task-01-structure-{p.id}"
                sec_list = ", ".join(f"#{s.id} ({s.purpose})" for s in p.sections)
                p_task = Task(
                    id=t_id,
                    run_id=self.run_id,
                    title=f"Page Layout: {p.title} ({p.file})",
                    description=(
                        f"Generate inner <main> content for page '{p.title}' ({p.file}). "
                        f"Sections: {sec_list}. Follow spec.json strictly. "
                        f"Use ONLY standard component classes from base.css (.container, .section, .hero, .grid, .card, .btn-primary, .btn-outline, .badge, .form, .testimonial, .pricing, .gallery, .faq, .stats)."
                    ),
                    role_hint="structure",
                    status="open",
                    priority=5,
                    target=p.file,
                    depends_on=["task-00-plan"]
                )
                self.blackboard.add_task(p_task)
                structure_task_ids.append(t_id)

            # Update styling, script, and QA tasks to depend on all structure tasks
            style_task = self.blackboard.get_task(self.run_id, "task-02-styling")
            if style_task:
                style_task.depends_on = ["task-00-plan"] + structure_task_ids
                style_task.description = (
                    "Write page-specific extras, animations, or accents in styles.css. "
                    "base.css is ALREADY PROVIDED with :root variables and full component library. "
                    "DO NOT redefine :root variables or duplicate base.css. DO NOT hardcode colors; use var(--...)."
                )
                self.blackboard.add_task(style_task)

            script_task = self.blackboard.get_task(self.run_id, "task-03-script")
            if script_task:
                script_task.depends_on = ["task-00-plan"] + structure_task_ids
                self.blackboard.add_task(script_task)

            qa_task = self.blackboard.get_task(self.run_id, "task-04-qa")
            if qa_task:
                qa_task.depends_on = ["task-00-plan"] + structure_task_ids + ["task-02-styling", "task-03-script"]
                self.blackboard.add_task(qa_task)

            self.blackboard.update_task_status(self.run_id, target_task.id, self.agent_id, "done")
            self.event_log.append(
                run_id=self.run_id,
                agent_id=self.agent_id,
                event_type="task_done",
                target="spec.json",
                payload={"task_id": target_task.id}
            )

            # Emit initial structure signal to awaken structure agent
            primary_file = spec.pages[0].file if spec.pages else "index.html"
            self.blackboard.emit_signal(self.run_id, "need_structure", primary_file, self.agent_id)
            self.current_task = None
            return True

        # For all other tasks, assemble prompt with shared spec.json contract
        existing_files = self.sandbox.list_files()
        target_file = target_task.target.split(",")[0].strip() if target_task.target else "index.html"
        current_content = ""
        if self.sandbox.file_exists(target_file):
            current_content = f"\nExisting content of '{target_file}':\n```\n{self.sandbox.read_file(target_file)}\n```\n"

        spec_contract = ""
        if self.sandbox.file_exists("spec.json"):
            spec_contract = f"\nSHARED SITE SPECIFICATION CONTRACT (spec.json - STRICTLY FOLLOW THIS):\n```json\n{self.sandbox.read_file('spec.json')}\n```\n"

        # Supply generated HTML pages and base design system context to style and script agents
        context_files = ""
        few_shot_block = ""
        starter_template_block = ""

        if target_file.endswith(".html") and self.sandbox.file_exists("spec.json"):
            from runtime.templates import get_few_shot_example, load_starter_template, fill_template_placeholders
            import json
            try:
                spec_raw = json.loads(self.sandbox.read_file("spec.json"))
                spec_obj = SiteSpec(**spec_raw)
                matching_page = next((p for p in spec_obj.pages if p.file == target_file), None)
                if not matching_page:
                    matching_page = PageSpec(id="page", file=target_file, title="Page", sections=[])

                few_shot_block = f"\nFEW-SHOT HIGH QUALITY <main> EXAMPLE (for site_type '{spec_obj.site_type}'):\n```html\n{get_few_shot_example(spec_obj.site_type)}\n```\n"

                raw_template = load_starter_template(spec_obj.site_type, target_file)
                if raw_template:
                    hydrated_template = fill_template_placeholders(raw_template, spec_obj, matching_page)
                    starter_template_block = (
                        f"\nHAND-CRAFTED STARTER TEMPLATE (Adapt this layout to satisfy the prompt's requirements):\n"
                        f"```html\n{hydrated_template}\n```\n"
                        f"Fill in realistic content matching the brand tone, retain standard component classes (.container, .section, .hero, .grid, .card, .btn), and satisfy all user requirements.\n"
                    )
            except Exception as e:
                logger.warning(f"Failed loading template context: {e}")

        elif target_file in ("styles.css", "script.js"):
            html_snippets = []
            for f in self.sandbox.list_files():
                if f.endswith(".html"):
                    html_snippets.append(f"--- {f} ---\n{self.sandbox.read_file(f)}")
            if html_snippets:
                context_files = f"\nGENERATED HTML MARKUP (match your code to these actual IDs and classes):\n```\n" + "\n\n".join(html_snippets) + "\n```\n"
            if target_file == "styles.css" and self.sandbox.file_exists("base.css"):
                context_files += (
                    f"\nNOTE: base.css is already active and provides :root variables and all base component styles.\n"
                    f"Write only page-specific overrides, animations, and accents in styles.css.\n"
                    f"DO NOT duplicate :root or use hard-coded colors; always use var(--...).\n"
                )
        elif target_file != "index.html" and self.sandbox.file_exists("index.html"):
            context_files = f"\nReference 'index.html' (match your selectors to this markup):\n```\n{self.sandbox.read_file('index.html')}\n```\n"

        user_prompt = f"""
OVERALL WEBSITE GOAL & REQUIREMENTS:
"{user_goal_prompt}"
{spec_contract}
Current Task: {target_task.title}
Task ID: {target_task.id}
Description: {target_task.description}
Target File: {target_file}
Existing files in workspace: {existing_files}
{current_content}
{few_shot_block}
{starter_template_block}
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

                # Deterministic HTML Page Assembly via Jinja2 (Phase 2 & 4)
                if file_path.endswith(".html") and self.sandbox.file_exists("spec.json"):
                    from runtime.render import render_full_page
                    from runtime.templates import load_starter_template, fill_template_placeholders
                    import json
                    try:
                        spec_raw = json.loads(self.sandbox.read_file("spec.json"))
                        spec_obj = SiteSpec(**spec_raw)
                        matching_page = next((p for p in spec_obj.pages if p.file == file_path), None)
                        if matching_page:
                            # Fall back to hydrated starter template if LLM output is empty or whitespace
                            if not file_content.strip():
                                tmpl = load_starter_template(spec_obj.site_type, file_path)
                                if tmpl:
                                    file_content = fill_template_placeholders(tmpl, spec_obj, matching_page)
                            file_content = render_full_page(spec_obj, matching_page, file_content)
                    except Exception as err:
                        logger.warning(f"Error compiling deterministic page HTML for '{file_path}': {err}")

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
