"""
QA Engine - Automated Verification & Defect Detection for Stage 2.
Performs deterministic audits of HTML, CSS, and JS assets in the sandbox.
Reports defects with targeted role hints for automated repair loops.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional
from runtime.sandbox import Sandbox


@dataclass
class QADefect:
    target: str
    role_hint: str
    severity: str  # "critical" | "high" | "medium" | "low"
    summary: str
    remediation: str


@dataclass
class QAAuditReport:
    passed: bool
    score: float
    defects: List[QADefect] = field(default_factory=list)
    checks_passed: List[str] = field(default_factory=list)


def audit_html(content: str) -> List[QADefect]:
    defects = []

    if "<!DOCTYPE HTML>" not in content.upper():
        defects.append(QADefect(
            target="index.html",
            role_hint="structure",
            severity="critical",
            summary="Missing <!DOCTYPE html> declaration",
            remediation="Add <!DOCTYPE html> as the very first line of index.html"
        ))

    if "<html" not in content or "</html>" not in content:
        defects.append(QADefect(
            target="index.html",
            role_hint="structure",
            severity="critical",
            summary="Missing <html> or </html> tags",
            remediation="Wrap the document in <html lang=\"en\"> ... </html>"
        ))

    if "<head>" not in content or "</head>" not in content:
        defects.append(QADefect(
            target="index.html",
            role_hint="structure",
            severity="critical",
            summary="Missing <head> section",
            remediation="Include a valid <head> element with meta charset, viewport, and title"
        ))

    if "viewport" not in content:
        defects.append(QADefect(
            target="index.html",
            role_hint="structure",
            severity="medium",
            summary="Missing responsive viewport meta tag",
            remediation="Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
        ))

    if 'href="styles.css"' not in content and "href='styles.css'" not in content:
        defects.append(QADefect(
            target="index.html",
            role_hint="structure",
            severity="high",
            summary="styles.css is not linked in index.html",
            remediation="Add <link rel=\"stylesheet\" href=\"styles.css\"> inside <head>"
        ))

    if "script.js" not in content:
        defects.append(QADefect(
            target="index.html",
            role_hint="structure",
            severity="high",
            summary="script.js is not referenced in index.html",
            remediation="Add <script src=\"script.js\" defer></script>"
        ))

    return defects


def audit_css(content: str) -> List[QADefect]:
    defects = []

    if "<!DOCTYPE" in content.upper() or "<HTML" in content.upper() or "<STYLE" in content.upper():
        defects.append(QADefect(
            target="styles.css",
            role_hint="style",
            severity="critical",
            summary="styles.css contains HTML markup instead of CSS rules",
            remediation="styles.css must contain only pure CSS stylesheet rules, not HTML tags"
        ))

    open_braces = content.count("{")
    close_braces = content.count("}")
    if open_braces != close_braces:
        defects.append(QADefect(
            target="styles.css",
            role_hint="style",
            severity="critical",
            summary=f"Unbalanced CSS braces ({open_braces} open vs {close_braces} close)",
            remediation="Fix mismatched curly braces in styles.css"
        ))

    if ":root" not in content and "--" not in content:
        defects.append(QADefect(
            target="styles.css",
            role_hint="style",
            severity="low",
            summary="No CSS custom variables detected",
            remediation="Define theme variables in a :root block (e.g., --bg-primary, --text-primary)"
        ))

    if "@media" not in content:
        defects.append(QADefect(
            target="styles.css",
            role_hint="style",
            severity="medium",
            summary="No media queries detected for responsive design",
            remediation="Add responsive breakpoints like @media (max-width: 768px)"
        ))

    return defects


def audit_js(content: str, html_content: Optional[str] = None) -> List[QADefect]:
    defects = []

    # Check bracket balance
    for open_b, close_b, name in [("{", "}", "curly braces"), ("(", ")", "parentheses"), ("[", "]", "square brackets")]:
        if content.count(open_b) != content.count(close_b):
            defects.append(QADefect(
                target="script.js",
                role_hint="script",
                severity="critical",
                summary=f"Unbalanced JS {name}",
                remediation=f"Ensure all {name} in script.js are properly closed"
            ))

    # Cross-reference querySelectors against HTML if available
    if html_content:
        selector_patterns = re.findall(r"querySelector(?:All)?\(['\"]([.#][a-zA-Z0-9_-]+)['\"]\)", content)
        for sel in selector_patterns:
            if sel.startswith("."):
                class_name = sel[1:]
                if f'class="{class_name}"' not in html_content and f"class='{class_name}'" not in html_content and class_name not in html_content:
                    defects.append(QADefect(
                        target="script.js",
                        role_hint="script",
                        severity="medium",
                        summary=f"JS selects class '{sel}' which does not exist in index.html",
                        remediation=f"Ensure index.html includes element with class '{class_name}' or update selector"
                    ))
            elif sel.startswith("#"):
                id_name = sel[1:]
                if f'id="{id_name}"' not in html_content and f"id='{id_name}'" not in html_content:
                    defects.append(QADefect(
                        target="script.js",
                        role_hint="script",
                        severity="medium",
                        summary=f"JS selects ID '{sel}' which does not exist in index.html",
                        remediation=f"Ensure index.html includes element with id '{id_name}' or update selector"
                    ))

    return defects


def run_qa_audit(sandbox: Sandbox) -> QAAuditReport:
    """Execute full automated QA verification suite against sandbox workspace."""
    defects: List[QADefect] = []
    checks_passed: List[str] = []

    # 1. Existence check
    html_exists = sandbox.file_exists("index.html")
    css_exists = sandbox.file_exists("styles.css")
    js_exists = sandbox.file_exists("script.js")

    if not html_exists:
        defects.append(QADefect(
            target="index.html",
            role_hint="structure",
            severity="critical",
            summary="index.html does not exist in sandbox",
            remediation="Generate index.html"
        ))
    else:
        checks_passed.append("File index.html exists")

    if not css_exists:
        defects.append(QADefect(
            target="styles.css",
            role_hint="style",
            severity="high",
            summary="styles.css does not exist in sandbox",
            remediation="Generate styles.css"
        ))
    else:
        checks_passed.append("File styles.css exists")

    if not js_exists:
        defects.append(QADefect(
            target="script.js",
            role_hint="script",
            severity="high",
            summary="script.js does not exist in sandbox",
            remediation="Generate script.js"
        ))
    else:
        checks_passed.append("File script.js exists")

    # 2. Content audits
    html_content = sandbox.read_file("index.html") if html_exists else ""
    css_content = sandbox.read_file("styles.css") if css_exists else ""
    js_content = sandbox.read_file("script.js") if js_exists else ""

    if html_content:
        html_defects = audit_html(html_content)
        if not html_defects:
            checks_passed.append("HTML structure and semantic tags valid")
        else:
            defects.extend(html_defects)

    if css_content:
        css_defects = audit_css(css_content)
        if not css_defects:
            checks_passed.append("CSS syntax and responsive rules valid")
        else:
            defects.extend(css_defects)

    if js_content:
        js_defects = audit_js(js_content, html_content=html_content)
        if not js_defects:
            checks_passed.append("JavaScript syntax and DOM selector links valid")
        else:
            defects.extend(js_defects)

    critical_count = sum(1 for d in defects if d.severity in ("critical", "high"))
    score = max(0.0, 100.0 - (len(defects) * 15.0))
    passed = (critical_count == 0) and html_exists and css_exists and js_exists

    return QAAuditReport(
        passed=passed,
        score=score,
        defects=defects,
        checks_passed=checks_passed
    )
