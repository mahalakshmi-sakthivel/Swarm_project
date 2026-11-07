"""
End-to-End Multi-Agent Swarm Test for Stage 2.
Tests all 5 specialized agents collaborating asynchronously:
- Coordinator Agent
- Structure Agent
- Style Agent
- Script Agent
- QA Agent
"""

import sys
sys.path.insert(0, ".")

import pytest
from runtime.blackboard import Blackboard
from runtime.events import EventLog
from runtime.llm import ActionPayload, InitialTasksPayload, QwenClient
from runtime.sandbox import Sandbox
from runtime.swarm import Swarm


@pytest.mark.asyncio
async def test_stage2_multi_agent_swarm_collaboration(tmp_path):
    db_file = str(tmp_path / "blackboard.db")
    blackboard = Blackboard(db_file)
    event_log = EventLog(db_file)
    sandbox = Sandbox(run_id="run_stage2_e2e", base_dir=str(tmp_path / ".sandbox"))
    run_id = "run_stage2_e2e"

    prompt = "Build a responsive dark-theme developer portfolio"

    mock_llm = QwenClient(model="mock_model")

    # Mock responses for the agents
    seeding_tasks = InitialTasksPayload(
        tasks=[
            {
                "id": "task-01-structure",
                "title": "Build HTML Structure",
                "description": "Semantic HTML5 markup with links to styles.css and script.js",
                "role_hint": "structure",
                "target": "index.html",
                "priority": 5
            },
            {
                "id": "task-02-styling",
                "title": "Build CSS Stylesheet",
                "description": "Dark theme styling with custom properties and responsive media queries",
                "role_hint": "style",
                "target": "styles.css",
                "priority": 4
            },
            {
                "id": "task-03-script",
                "title": "Build Interactive JavaScript",
                "description": "Mobile menu toggle and smooth scroll behavior",
                "role_hint": "script",
                "target": "script.js",
                "priority": 3
            },
            {
                "id": "task-04-qa",
                "title": "QA Audit",
                "description": "Verify assets and link integrity",
                "role_hint": "qa",
                "target": "all",
                "priority": 1
            }
        ]
    )

    valid_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Swarm Portfolio</title>
  <link rel="stylesheet" href="styles.css">
  <script src="script.js" defer></script>
</head>
<body>
  <nav class="navbar"><button class="mobile-menu-btn">Menu</button><ul class="nav-links"><li><a href="#home">Home</a></li></ul></nav>
  <header class="hero" id="home"><h1>Developer</h1></header>
  <section id="skills"><h2>Skills</h2></section>
  <section id="projects"><h2>Projects</h2></section>
  <footer id="contact"><p>Contact</p></footer>
</body>
</html>"""

    valid_css = """:root { --bg-primary: #0a0a0f; --text-primary: #fff; }
body { background: var(--bg-primary); color: var(--text-primary); margin: 0; }
.navbar { display: flex; justify-content: space-between; }
@media (max-width: 768px) { .nav-links { display: none; } }"""

    valid_js = """const btn = document.querySelector('.mobile-menu-btn');
if (btn) {
  btn.addEventListener('click', () => {
    const nav = document.querySelector('.nav-links');
    if (nav) nav.classList.toggle('active');
  });
}"""

    async def mock_generate(system_prompt: str, user_prompt: str, schema, **kwargs):
        if schema == InitialTasksPayload:
            return seeding_tasks

        if "task-02-styling" in user_prompt or "Target File: styles.css" in user_prompt:
            return ActionPayload(
                action="write_file",
                task_id="task-02-styling",
                target="styles.css",
                args={"path": "styles.css", "content": valid_css},
                reasoning_summary="Generated dark-theme CSS"
            )
        elif "task-03-script" in user_prompt or "Target File: script.js" in user_prompt:
            return ActionPayload(
                action="write_file",
                task_id="task-03-script",
                target="script.js",
                args={"path": "script.js", "content": valid_js},
                reasoning_summary="Generated client-side interaction script"
            )
        elif "task-01-structure" in user_prompt or "Target File: index.html" in user_prompt:
            return ActionPayload(
                action="write_file",
                task_id="task-01-structure",
                target="index.html",
                args={"path": "index.html", "content": valid_html},
                reasoning_summary="Generated semantic HTML5 layout"
            )
        else:
            return ActionPayload(action="task_done", task_id="task-04-qa")

    mock_llm.generate_structured = mock_generate

    swarm = Swarm(
        run_id=run_id,
        goal_prompt=prompt,
        blackboard=blackboard,
        event_log=event_log,
        sandbox=sandbox,
        llm_client=mock_llm
    )

    result = await swarm.run(max_seconds=15.0, poll_interval=0.2)

    # Assertions
    assert result["converged"] is True
    assert result["qa_passed"] is True
    assert result["completed_tasks"] >= 4

    # Verify generated sandbox assets
    assert sandbox.file_exists("index.html")
    assert sandbox.file_exists("styles.css")
    assert sandbox.file_exists("script.js")

    # Verify event trace includes contributions from multiple agents
    events = event_log.get_events(run_id)
    agents_in_trace = {e.agent_id for e in events}
    assert len(agents_in_trace) >= 4  # multiple specialized agents participated

    event_types = {e.event_type for e in events}
    assert "agent_spawned" in event_types
    assert "task_claimed" in event_types
    assert "file_edit" in event_types
    assert "task_done" in event_types
    assert "test_run" in event_types
