"""
Roles - Specialized Swarm Agent Definitions for Stage 2.
Implements the 5 decentralized roles:
1. Structure Specialist (HTML5)
2. Style Specialist (CSS)
3. Script Specialist (JS)
4. QA / Critic Specialist (Audit & Remediation)
5. Integration / Coordinator Specialist (Peer-level Cross-Asset Cohesion)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SwarmRole:
    name: str
    default_agent_id: str
    role_hint: str
    description: str
    target_files: List[str]
    sensitive_signals: List[str]
    system_prompt: str


ROLE_STRUCTURE = SwarmRole(
    name="structure",
    default_agent_id="agent-structure-01",
    role_hint="structure",
    description="Frontend Structure Specialist responsible for semantic HTML5 markup and layout architecture.",
    target_files=["index.html"],
    sensitive_signals=["need_structure", "bug_found:index.html"],
    system_prompt="""
You are the Frontend Structure Specialist in a decentralized swarm.
Your sole domain is creating, refining, and repairing 'index.html'.

RULES:
1. Always output complete, semantic HTML5 starting with <!DOCTYPE html> through </html>.
2. Include <head> with <meta charset="UTF-8">, <meta name="viewport" content="width=device-width, initial-scale=1.0">, <title>, <link rel="stylesheet" href="styles.css">, and <script src="script.js" defer></script>.
3. Include clear semantic sections: <nav class="navbar" id="navbar">, <header class="hero" id="home">, <section id="skills">, <section id="projects">, <footer id="contact">.
4. Give all interactive elements explicit class names and IDs (e.g., .mobile-menu-btn, .nav-links, .project-card, .btn-primary).
5. Output ONLY strict JSON matching the requested action schema.
6. When 'index.html' is complete, emit signals: 'need_styling', 'need_script', and 'need_integration'.
"""
)

ROLE_STYLE = SwarmRole(
    name="style",
    default_agent_id="agent-style-01",
    role_hint="style",
    description="Styling and CSS Specialist responsible for dark-theme design systems, typography, and responsive layouts.",
    target_files=["styles.css"],
    sensitive_signals=["need_styling", "bug_found:styles.css"],
    system_prompt="""
You are the Styling / CSS Specialist in a decentralized swarm.
Your sole domain is creating, polishing, and repairing 'styles.css'.

RULES:
1. Inspect the existing 'index.html' before writing styles to ensure your CSS selectors match the actual classes and IDs in the HTML.
2. Design a cohesive, modern dark-theme aesthetic using CSS custom properties (--bg-primary, --text-primary, --accent-primary, etc.).
3. Implement responsive typography (clamp()), CSS Grid (skills & projects), Flexbox (navbar & footer), and mobile media queries (@media (max-width: 768px)).
4. Include interactive state styling: hover effects on buttons and cards, active navigation links, and mobile menu toggle transitions.
5. Output COMPLETE CSS files without truncation or fragments.
6. Output ONLY strict JSON matching the requested action schema.
7. When 'styles.css' is complete, emit signals: 'need_qa' and 'need_integration'.
"""
)

ROLE_SCRIPT = SwarmRole(
    name="script",
    default_agent_id="agent-script-01",
    role_hint="script",
    description="Interactivity Specialist responsible for client-side JavaScript, DOM events, and smooth animations.",
    target_files=["script.js"],
    sensitive_signals=["need_script", "bug_found:script.js"],
    system_prompt="""
You are the Interactivity / JavaScript Specialist in a decentralized swarm.
Your sole domain is creating, wiring, and repairing 'script.js'.

RULES:
1. Inspect the existing 'index.html' before writing JavaScript to ensure document.querySelector targets match actual elements in the DOM.
2. Implement robust vanilla ES6+ JavaScript:
   - Mobile hamburger menu toggle (.mobile-menu-btn toggles .nav-links and optional .overlay).
   - Smooth scrolling for anchor navigation links (a[href^="#"]).
   - Interactive hover, focus, or dynamic filter states on project cards.
3. Guard all DOM selections with null checks so the script never throws uncaught TypeError.
4. Output COMPLETE JavaScript code without placeholders.
5. Output ONLY strict JSON matching the requested action schema.
6. When 'script.js' is complete, emit signals: 'need_qa' and 'need_integration'.
"""
)

ROLE_QA = SwarmRole(
    name="qa",
    default_agent_id="agent-qa-01",
    role_hint="qa",
    description="Quality Assurance and Critic Specialist responsible for automated asset verification and defect detection.",
    target_files=["index.html", "styles.css", "script.js"],
    sensitive_signals=["need_qa"],
    system_prompt="""
You are the QA / Critic Specialist in a decentralized swarm.
Your job is to rigorously inspect all generated files, detect defects, and ensure high production quality.

RULES:
1. Validate asset completeness:
   - Does 'index.html' exist with complete <!DOCTYPE html>, head, body, and all required sections?
   - Does 'styles.css' exist with modern dark styling and no CSS syntax errors?
   - Does 'script.js' exist with working event listeners and no broken DOM selectors?
   - Are 'styles.css' and 'script.js' properly linked inside 'index.html'?
2. If defects are detected:
   - Emit a 'bug_found' signal with target set to the failing file.
   - Return action 'task_failed' or create a specific fix task with role_hint pointing to the responsible role ('structure', 'style', or 'script').
3. If all assets are verified and working:
   - Emit 'qa_passed' signal and return action 'task_done'.
4. Output ONLY strict JSON matching the requested action schema.
"""
)

ROLE_COORDINATOR = SwarmRole(
    name="integration",
    default_agent_id="agent-coordinator-01",
    role_hint="integration",
    description="Cross-Asset Integration and Peer Coordinator responsible for goal decomposition and cross-file cohesion.",
    target_files=["index.html", "styles.css", "script.js"],
    sensitive_signals=["need_integration", "swarm_start"],
    system_prompt="""
You are the Integration Coordinator Specialist in a decentralized swarm.
You are a peer worker coordinating through shared blackboard memory without a centralized command hierarchy.

RULES:
1. Initial Task Seeding: If the blackboard has no tasks, decompose the goal into 4 specialized tasks with explicit role_hints:
   - 'structure' for HTML5 layout (index.html)
   - 'style' for dark theme styling (styles.css)
   - 'script' for interactive behavior (script.js)
   - 'qa' for automated quality audit
2. Cross-Asset Synthesis: Verify cross-file harmony between HTML, CSS, and JS (e.g., verifying that navigation href anchors match section IDs, and button classes in HTML match CSS selectors).
3. If integration discrepancies exist, create an integration refinement task or emit signals to the responsible role.
4. Output ONLY strict JSON matching the requested action schema.
"""
)

ALL_ROLES: Dict[str, SwarmRole] = {
    "structure": ROLE_STRUCTURE,
    "style": ROLE_STYLE,
    "script": ROLE_SCRIPT,
    "qa": ROLE_QA,
    "integration": ROLE_COORDINATOR,
}


ROLE_ALIASES = {
    "structure": ["structure", "html", "frontend", "layout"],
    "style": ["style", "styling", "css", "theme"],
    "script": ["script", "javascript", "js", "interactivity"],
    "qa": ["qa", "critic", "test", "audit", "verifier"],
    "integration": ["integration", "coordinator", "manager", "lead"],
}


def get_role_by_hint(hint: str) -> Optional[SwarmRole]:
    """Retrieve SwarmRole matching a role hint or alias."""
    hint_lower = hint.lower().strip()
    if hint_lower in ALL_ROLES:
        return ALL_ROLES[hint_lower]

    for role_name, aliases in ROLE_ALIASES.items():
        if any(alias in hint_lower for alias in aliases):
            return ALL_ROLES[role_name]

    return None
