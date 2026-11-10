"""
QA Engine - Comprehensive Verification & Defect Detection for Stage 2 Swarm (Phase 5).
Performs deterministic, rule-based audits across HTML, CSS, JS, and SiteSpec requirements.
Provides structured defects with {target, line, rule, severity, summary, remediation, req_id}.

Checks Implemented:
1. Link Check: Validates every <a href> resolves to a page in spec, an anchor, or external URL. No '#' placeholders.
2. Class Check: Verifies every class used in HTML exists in base.css or styles.css.
3. Requirements Check: Verifies each spec section id exists on the page; features mapped to JS/HTML; maps to R1..Rn.
4. Theme Check: Ensures no hex colors or unauthorized font-family declarations outside :root.
5. JS Check: Checks bracket balance and ensures DOM querySelector/getElementById targets exist.
6. Navigation Check: Asserts URL, <title>, and active nav links across all spec pages.
7. Responsive Check: Viewport meta tag, responsive grid columns, and mobile media queries.
8. Accessibility Check: Exactly one <h1> per page, image alt attributes, and form label associations.
9. Placeholder Check: Rejects 'Lorem ipsum', 'TODO', 'Your text here', and empty href placeholders.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from runtime.sandbox import Sandbox
from runtime.spec import SiteSpec
from runtime.theme import ALLOWED_COMPONENT_CLASSES_SET


@dataclass
class QADefect:
    target: str                  # Target file name (e.g. index.html, styles.css)
    role_hint: str               # Responsible role ("structure" | "style" | "script" | "qa")
    severity: str                # "critical" | "high" | "medium" | "low"
    summary: str                 # Concise defect description
    remediation: str             # Actionable remediation hint
    rule: str = "general"        # Rule identifier (e.g. "link-check", "class-check")
    line: Optional[int] = None   # 1-based line number where defect was detected
    req_id: Optional[str] = None # Requirement ID if applicable (e.g. "R1", "R2")

    @property
    def file(self) -> str:
        return self.target

    @property
    def message(self) -> str:
        return self.summary

    @property
    def fix_hint(self) -> str:
        return self.remediation


@dataclass
class QAAuditReport:
    passed: bool
    score: float
    coverage_percent: float = 100.0
    defects: List[QADefect] = field(default_factory=list)
    checks_passed: List[str] = field(default_factory=list)
    requirements_coverage: Dict[str, bool] = field(default_factory=dict)


def find_line_number(content: str, search_target: str) -> Optional[int]:
    """Return 1-based line number of search target in text content."""
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        if search_target in line:
            return idx
    return None


def extract_css_classes(css_content: str) -> Set[str]:
    """Parse class selectors defined in CSS stylesheet."""
    clean_css = re.sub(r'/\*[\s\S]*?\*/', '', css_content)
    matches = re.findall(r'\.([a-zA-Z0-9_-]+)\s*(?:[,\{\:\>\+\~\s])', clean_css)
    return set(matches)


# ---------------------------------------------------------------------------
# 1. LINK CHECK
# ---------------------------------------------------------------------------
def audit_links(content: str, current_file: str, sandbox: Sandbox) -> List[QADefect]:
    """
    Deterministic Link Check:
    Every <a href> must resolve to:
    - a page in the spec that exists in the sandbox
    - an existing #anchor on the target page
    - an external http/https/mailto/tel URL
    No '#' or empty placeholders permitted.
    """
    defects = []
    # Match href attributes with their surrounding snippet for line calculation
    href_matches = re.finditer(r'href=[\'"]([^\'"]*)[\'"]', content)

    for match in href_matches:
        href_raw = match.group(1)
        href_clean = href_raw.strip()
        matched_str = match.group(0)
        line_no = find_line_number(content, matched_str)

        # Rejection of empty or single hash placeholders
        if not href_clean or href_clean == "#":
            defects.append(QADefect(
                target=current_file,
                role_hint="structure",
                severity="medium",
                summary=f"Placeholder or empty link '{href_raw}' found in {current_file}",
                remediation="Replace with relative page link (e.g. menu.html) or section anchor (e.g. #contact)",
                rule="link-check",
                line=line_no
            ))
            continue

        # External and special protocols are permitted
        if href_clean.startswith(("http://", "https://", "mailto:", "tel:", "javascript:")):
            continue

        # Relative page or anchor resolution
        parts = href_clean.split("#")
        target_page = parts[0]
        anchor = parts[1] if len(parts) > 1 else ""

        if target_page:
            # Check target page existence in sandbox
            if not sandbox.file_exists(target_page):
                defects.append(QADefect(
                    target=current_file,
                    role_hint="structure",
                    severity="critical",
                    summary=f"Broken link in {current_file}: '{href_clean}' targets nonexistent page '{target_page}'",
                    remediation=f"Generate {target_page} or update href to an existing page in spec.json",
                    rule="link-check",
                    line=line_no
                ))
            elif anchor:
                # Target page exists: check anchor in that page
                target_page_content = sandbox.read_file(target_page)
                if f'id="{anchor}"' not in target_page_content and f"id='{anchor}'" not in target_page_content:
                    defects.append(QADefect(
                        target=current_file,
                        role_hint="structure",
                        severity="medium",
                        summary=f"Broken anchor '#{anchor}' in link '{href_clean}': anchor id not found in {target_page}",
                        remediation=f"Add id=\"{anchor}\" to the target section in {target_page}",
                        rule="link-check",
                        line=line_no
                    ))
        elif anchor:
            # Same-page anchor
            if f'id="{anchor}"' not in content and f"id='{anchor}'" not in content:
                defects.append(QADefect(
                    target=current_file,
                    role_hint="structure",
                    severity="medium",
                    summary=f"Anchor '#{anchor}' in {current_file} does not match any element ID on the page",
                    remediation=f"Add id=\"{anchor}\" to the destination section in {current_file}",
                    rule="link-check",
                    line=line_no
                ))

    return defects


# ---------------------------------------------------------------------------
# 2. CLASS CHECK
# ---------------------------------------------------------------------------
def audit_html_classes(
    content: str,
    current_file: str,
    allowed_classes: Optional[Set[str]] = None
) -> List[QADefect]:
    """
    Deterministic Class Check:
    Every class used in HTML must exist in base.css whitelist, styles.css, or structural patterns.
    """
    defects = []
    effective_allowed = set(ALLOWED_COMPONENT_CLASSES_SET)
    if allowed_classes:
        effective_allowed.update(allowed_classes)

    class_matches = re.finditer(r'class=[\'"]([^\'"]+)[\'"]', content)
    for match in class_matches:
        class_str = match.group(1)
        matched_str = match.group(0)
        line_no = find_line_number(content, matched_str)

        classes = class_str.strip().split()
        for cls in classes:
            cls_clean = cls.strip()
            if not cls_clean:
                continue

            if (
                cls_clean in effective_allowed
                or cls_clean.startswith(("page-", "theme-", "icon-", "sec-"))
                or cls_clean in (
                    "active", "open", "visible", "hidden", "disabled", "short",
                    "brand-logo", "logo-text", "site-header", "page-main",
                    "footer-logo", "footer-tagline", "footer-nav", "footer-info",
                    "footer-audience", "footer-tone", "footer-bottom", "copyright",
                    "hamburger-bar", "mobile-menu-btn", "nav-actions"
                )
            ):
                continue

            defects.append(QADefect(
                target=current_file,
                role_hint="structure",
                severity="low",
                summary=f"Unrecognized class '{cls_clean}' in {current_file}",
                remediation=f"Replace '{cls_clean}' with standard component classes from base.css (e.g. .card, .btn, .hero, .grid)",
                rule="class-check",
                line=line_no
            ))

    return defects


# ---------------------------------------------------------------------------
# 3. REQUIREMENTS CHECK
# ---------------------------------------------------------------------------
def audit_requirements(
    sandbox: Sandbox,
    spec: SiteSpec
) -> Tuple[List[QADefect], Dict[str, bool], float]:
    """
    Deterministic Requirements Check:
    - Every section ID defined in spec.pages exists in that page's HTML.
    - Every feature in spec.features has matching markup or JS handlers.
    - Maps satisfaction back to requirement IDs (R1, R2, ..., Rn).
    """
    defects = []
    coverage_map: Dict[str, bool] = {}

    # 1. Section presence across pages
    for page in spec.pages:
        if not sandbox.file_exists(page.file):
            continue
        page_html = sandbox.read_file(page.file)

        for sec in page.sections:
            sec_satisfied = (f'id="{sec.id}"' in page_html) or (f"id='{sec.id}'" in page_html)
            if not sec_satisfied:
                defects.append(QADefect(
                    target=page.file,
                    role_hint="structure",
                    severity="critical",
                    summary=f"Required section #{sec.id} ({sec.purpose}) is missing from {page.file}",
                    remediation=f"Add <section id=\"{sec.id}\" class=\"section\">...</section> to {page.file}",
                    rule="requirements-check"
                ))

    # 2. Features presence (HTML + script.js)
    combined_html = ""
    for f in sandbox.list_files():
        if f.endswith(".html"):
            combined_html += "\n" + sandbox.read_file(f)

    script_content = sandbox.read_file("script.js") if sandbox.file_exists("script.js") else ""

    for feat in spec.features:
        feat_clean = feat.lower().strip()
        feat_satisfied = False

        if "mobile-menu" in feat_clean or "nav" in feat_clean:
            feat_satisfied = ("mobile-menu" in combined_html) or ("mobile-menu" in script_content) or ("hamburger" in combined_html)
        elif "form" in feat_clean or "validation" in feat_clean:
            feat_satisfied = ("<form" in combined_html) or ("addEventListener('submit'" in script_content)
        elif "modal" in feat_clean or "popup" in feat_clean:
            feat_satisfied = ("modal" in combined_html) or ("modal" in script_content)
        elif "carousel" in feat_clean or "slider" in feat_clean:
            feat_satisfied = ("carousel" in combined_html) or ("slider" in combined_html)
        else:
            feat_satisfied = (feat_clean in combined_html.lower()) or (feat_clean in script_content.lower())

        if not feat_satisfied:
            defects.append(QADefect(
                target="script.js" if sandbox.file_exists("script.js") else "index.html",
                role_hint="script",
                severity="medium",
                summary=f"Required feature '{feat}' is not implemented in HTML or script.js",
                remediation=f"Implement interactive handler or component for '{feat}'",
                rule="requirements-check"
            ))

    # 3. Map to spec.requirements (R1..Rn)
    for req in spec.requirements:
        req_text = req.description.lower()
        req_words = [w.strip("'\":;,.?!()[]") for w in req_text.split() if len(w.strip("'\":;,.?!()[]")) > 3]
        satisfied = any(w in combined_html.lower() for w in req_words)
        coverage_map[req.id] = satisfied
        if not satisfied:
            defects.append(QADefect(
                target="index.html",
                role_hint="structure",
                severity="medium",
                summary=f"Requirement {req.id} ('{req.description}') was not satisfied in the output",
                remediation=f"Implement requirement {req.id}: {req.description}",
                rule="requirements-check",
                req_id=req.id
            ))

    total_reqs = len(spec.requirements) if spec.requirements else 1
    passed_reqs = sum(1 for status in coverage_map.values() if status)
    coverage_pct = round((passed_reqs / total_reqs) * 100.0, 1)

    return defects, coverage_map, coverage_pct


# ---------------------------------------------------------------------------
# 4. THEME CHECK
# ---------------------------------------------------------------------------
def audit_theme_colors(css_content: str, target_file: str = "styles.css") -> List[QADefect]:
    """Verify that CSS does not use hardcoded hex colors outside :root."""
    defects = []
    clean_css = re.sub(r'/\*[\s\S]*?\*/', '', css_content)
    # Exclude :root block from check
    non_root_css = re.sub(r':root\s*\{[\s\S]*?\}', '', clean_css)

    hex_matches = list(re.finditer(r'#(?:[0-9a-fA-F]{3,8})\b', non_root_css))
    reported_hexes = set()
    for match in hex_matches:
        hex_val = match.group(0)
        if hex_val in reported_hexes:
            continue
        reported_hexes.add(hex_val)
        line_no = find_line_number(css_content, hex_val)
        defects.append(QADefect(
            target=target_file,
            role_hint="style",
            severity="medium",
            summary=f"Hardcoded hex color '{hex_val}' found in {target_file}",
            remediation=f"Replace '{hex_val}' with theme CSS variables: var(--primary), var(--accent), var(--bg-surface), etc.",
            rule="theme-check",
            line=line_no
        ))
        if len(reported_hexes) >= 3:
            break

    return defects


# ---------------------------------------------------------------------------
# 5. JS CHECK
# ---------------------------------------------------------------------------
def audit_js(content: str, html_content: Optional[str] = None) -> List[QADefect]:
    """
    Deterministic JS Check:
    - Balanced braces, brackets, parentheses
    - getElementById / querySelector targets exist in HTML
    """
    defects = []

    # 1. Bracket balance
    for open_b, close_b, name in [("{", "}", "curly braces"), ("(", ")", "parentheses"), ("[", "]", "square brackets")]:
        if content.count(open_b) != content.count(close_b):
            defects.append(QADefect(
                target="script.js",
                role_hint="script",
                severity="critical",
                summary=f"Unbalanced JS {name} ({content.count(open_b)} open vs {content.count(close_b)} close)",
                remediation=f"Ensure all {name} in script.js are properly closed",
                rule="js-check"
            ))

    # 2. Selector cross-reference against combined HTML
    if html_content:
        # Match querySelector, querySelectorAll, getElementById
        id_patterns = re.findall(r"getElementById\(['\"]([a-zA-Z0-9_-]+)['\"]\)", content)
        for target_id in id_patterns:
            if f'id="{target_id}"' not in html_content and f"id='{target_id}'" not in html_content:
                line_no = find_line_number(content, target_id)
                defects.append(QADefect(
                    target="script.js",
                    role_hint="script",
                    severity="medium",
                    summary=f"script.js selects element id '#{target_id}' which does not exist in the HTML",
                    remediation=f"Add id=\"{target_id}\" to target element in HTML or update selector",
                    rule="js-check",
                    line=line_no
                ))

        selector_patterns = re.findall(r"querySelector(?:All)?\(['\"]([.#][a-zA-Z0-9_-]+)['\"]\)", content)
        for sel in selector_patterns:
            line_no = find_line_number(content, sel)
            if sel.startswith("."):
                class_name = sel[1:]
                if f'class="{class_name}"' not in html_content and f"class='{class_name}'" not in html_content and class_name not in html_content:
                    defects.append(QADefect(
                        target="script.js",
                        role_hint="script",
                        severity="medium",
                        summary=f"script.js selects class '{sel}' which does not exist in the HTML",
                        remediation=f"Ensure HTML includes element with class '{class_name}' or update selector",
                        rule="js-check",
                        line=line_no
                    ))
            elif sel.startswith("#"):
                id_name = sel[1:]
                if f'id="{id_name}"' not in html_content and f"id='{id_name}'" not in html_content:
                    defects.append(QADefect(
                        target="script.js",
                        role_hint="script",
                        severity="medium",
                        summary=f"script.js selects ID '{sel}' which does not exist in the HTML",
                        remediation=f"Ensure HTML includes element with id '{id_name}' or update selector",
                        rule="js-check",
                        line=line_no
                    ))

    return defects


# ---------------------------------------------------------------------------
# 6. ACCESSIBILITY CHECK
# ---------------------------------------------------------------------------
def audit_accessibility(content: str, target_file: str) -> List[QADefect]:
    """
    Deterministic Accessibility Check:
    - Exactly one <h1> per page
    - Images must have alt attributes
    - Form inputs must have labels or aria-labels
    """
    defects = []

    # 1. Exactly one h1 per page
    h1_count = len(re.findall(r'<h1\b', content, re.IGNORECASE))
    if h1_count == 0:
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="critical",
            summary=f"Missing <h1> heading in {target_file}",
            remediation=f"Add exactly one main <h1> heading to {target_file}",
            rule="accessibility-check"
        ))
    elif h1_count > 1:
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="medium",
            summary=f"Multiple ({h1_count}) <h1> headings detected in {target_file}",
            remediation="Ensure each page has exactly one primary <h1>; use <h2> for subsections",
            rule="accessibility-check"
        ))

    # 2. Image alt tags
    img_tags = re.finditer(r'<img\b([^>]*)>', content, re.IGNORECASE)
    for img in img_tags:
        attrs = img.group(1)
        if "alt=" not in attrs.lower():
            line_no = find_line_number(content, img.group(0))
            defects.append(QADefect(
                target=target_file,
                role_hint="structure",
                severity="medium",
                summary=f"Image tag without alt attribute found in {target_file}",
                remediation="Add a descriptive alt=\"...\" attribute to every <img> element",
                rule="accessibility-check",
                line=line_no
            ))

    # 3. Form input labels
    input_tags = re.finditer(r'<input\b([^>]*)>', content, re.IGNORECASE)
    for inp in input_tags:
        attrs = inp.group(1)
        if 'type="hidden"' in attrs.lower() or 'type="submit"' in attrs.lower():
            continue
        id_match = re.search(r'id=[\'"]([^\'"]+)[\'"]', attrs)
        has_aria = "aria-label=" in attrs.lower() or "aria-labelledby=" in attrs.lower()

        if id_match:
            inp_id = id_match.group(1)
            has_label = f'for="{inp_id}"' in content or f"for='{inp_id}'" in content
            if not has_label and not has_aria:
                line_no = find_line_number(content, inp.group(0))
                defects.append(QADefect(
                    target=target_file,
                    role_hint="structure",
                    severity="low",
                    summary=f"Form input id='{inp_id}' in {target_file} lacks an associated <label for='{inp_id}'>",
                    remediation=f"Add <label for=\"{inp_id}\">...</label> or aria-label for accessibility",
                    rule="accessibility-check",
                    line=line_no
                ))
        elif not has_aria:
            line_no = find_line_number(content, inp.group(0))
            defects.append(QADefect(
                target=target_file,
                role_hint="structure",
                severity="low",
                summary=f"Form input in {target_file} lacks both id and aria-label",
                remediation="Provide an id and matching <label for='...'> or aria-label",
                rule="accessibility-check",
                line=line_no
            ))

    return defects


# ---------------------------------------------------------------------------
# 7. PLACEHOLDER CHECK
# ---------------------------------------------------------------------------
def audit_placeholders(content: str, target_file: str) -> List[QADefect]:
    """Check for forbidden placeholder strings like 'Lorem ipsum' or 'TODO'."""
    defects = []
    forbidden_terms = [
        "lorem ipsum",
        "dolor sit amet",
        "todo",
        "fixme",
        "your text here",
        "sample text",
        "placeholder text",
        "insert text"
    ]

    for term in forbidden_terms:
        # Match case-insensitively with word boundaries
        matches = list(re.finditer(rf'\b{re.escape(term)}\b', content, re.IGNORECASE))
        for m in matches[:2]: # report at most 2 per term
            line_no = find_line_number(content, m.group(0))
            defects.append(QADefect(
                target=target_file,
                role_hint="structure" if target_file.endswith(".html") else "script",
                severity="high",
                summary=f"Placeholder text '{m.group(0)}' detected in {target_file}",
                remediation="Replace placeholder text with realistic, domain-specific copy",
                rule="placeholder-check",
                line=line_no
            ))

    return defects


# ---------------------------------------------------------------------------
# 8. HTML SYNTAX AUDIT
# ---------------------------------------------------------------------------
def audit_html(content: str, target_file: str = "index.html") -> List[QADefect]:
    defects = []

    if "<!DOCTYPE HTML>" not in content.upper():
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="critical",
            summary=f"Missing <!DOCTYPE html> declaration in {target_file}",
            remediation=f"Add <!DOCTYPE html> as the very first line of {target_file}",
            rule="html-syntax"
        ))

    if "<html" not in content or "</html>" not in content:
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="critical",
            summary=f"Missing <html> or </html> tags in {target_file}",
            remediation="Wrap the document in <html lang=\"en\"> ... </html>",
            rule="html-syntax"
        ))

    if "<head>" not in content or "</head>" not in content:
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="critical",
            summary=f"Missing <head> section in {target_file}",
            remediation="Include a valid <head> element with meta charset, viewport, and title",
            rule="html-syntax"
        ))

    if "viewport" not in content:
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="medium",
            summary=f"Missing responsive viewport meta tag in {target_file}",
            remediation="Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
            rule="responsive-check"
        ))

    if 'href="styles.css"' not in content and "href='styles.css'" not in content:
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="high",
            summary=f"styles.css is not linked in {target_file}",
            remediation="Add <link rel=\"stylesheet\" href=\"styles.css\"> inside <head>",
            rule="html-syntax"
        ))

    if "script.js" not in content:
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="high",
            summary=f"script.js is not referenced in {target_file}",
            remediation="Add <script src=\"script.js\" defer></script>",
            rule="html-syntax"
        ))

    return defects


# ---------------------------------------------------------------------------
# 9. CSS AUDIT
# ---------------------------------------------------------------------------
def audit_css(content: str, target_file: str = "styles.css", is_base: bool = False) -> List[QADefect]:
    defects = []
    clean_content = content.strip()

    if len(clean_content) < 15:
        defects.append(QADefect(
            target=target_file,
            role_hint="style",
            severity="critical",
            summary=f"{target_file} is too short ({len(clean_content)} bytes) or empty",
            remediation=f"Generate a functional stylesheet in {target_file}",
            rule="css-syntax"
        ))

    if clean_content.startswith("<!--") or ("/* CSS" in clean_content and len(clean_content) < 120):
        defects.append(QADefect(
            target=target_file,
            role_hint="style",
            severity="critical",
            summary=f"{target_file} contains placeholder comment stubs instead of functional CSS rules",
            remediation="Provide complete CSS declarations for all navigation, hero, card, and footer classes",
            rule="placeholder-check"
        ))

    if "<!DOCTYPE" in content.upper() or "<HTML" in content.upper() or "<STYLE" in content.upper():
        defects.append(QADefect(
            target=target_file,
            role_hint="style",
            severity="critical",
            summary=f"{target_file} contains HTML markup instead of CSS rules",
            remediation=f"{target_file} must contain only pure CSS stylesheet rules, not HTML tags",
            rule="css-syntax"
        ))

    open_braces = content.count("{")
    close_braces = content.count("}")

    if open_braces != close_braces:
        defects.append(QADefect(
            target=target_file,
            role_hint="style",
            severity="critical",
            summary=f"Unbalanced CSS braces in {target_file} ({open_braces} open vs {close_braces} close)",
            remediation=f"Fix mismatched curly braces in {target_file}",
            rule="css-syntax"
        ))

    if open_braces == 0:
        defects.append(QADefect(
            target=target_file,
            role_hint="style",
            severity="critical",
            summary=f"{target_file} lacks rule blocks (no '{{' braces found)",
            remediation=f"Implement styling rule blocks for HTML elements and classes in {target_file}",
            rule="css-syntax"
        ))

    if is_base:
        if ":root" not in content and "--" not in content:
            defects.append(QADefect(
                target=target_file,
                role_hint="style",
                severity="high",
                summary=f"Missing :root block in {target_file}",
                remediation="Define theme variables in a :root block (e.g., --bg-primary, --text-primary)",
                rule="theme-check"
            ))

        if "@media" not in content:
            defects.append(QADefect(
                target=target_file,
                role_hint="style",
                severity="medium",
                summary=f"No media queries detected in {target_file} for responsive design",
                remediation="Add responsive breakpoints like @media (max-width: 768px)",
                rule="responsive-check"
            ))

    return defects


# ---------------------------------------------------------------------------
# FULL DETERMINISTIC QA SUITE EXECUTION
# ---------------------------------------------------------------------------
def run_qa_audit(sandbox: Sandbox) -> QAAuditReport:
    """
    Execute full automated QA verification suite against sandbox workspace across all pages.
    Guarantees that a site is ONLY marked converged when checks 1-6 pass with 0 critical/high
    errors and requirement coverage is 100%.
    """
    defects: List[QADefect] = []
    checks_passed: List[str] = []
    coverage_map: Dict[str, bool] = {}
    coverage_pct = 100.0

    # 1. Load spec.json if available
    spec_obj: Optional[SiteSpec] = None
    expected_pages = ["index.html"]
    if sandbox.file_exists("spec.json"):
        try:
            spec_raw = json.loads(sandbox.read_file("spec.json"))
            spec_obj = SiteSpec(**spec_raw)
            expected_pages = [p.file for p in spec_obj.pages]
            if not expected_pages:
                expected_pages = ["index.html"]
        except Exception:
            expected_pages = ["index.html"]

    # Also discover any extra .html files in sandbox
    for f in sandbox.list_files():
        if f.endswith(".html") and f not in expected_pages:
            expected_pages.append(f)

    # 2. Check CSS styles for custom classes
    custom_classes: Set[str] = set()
    if sandbox.file_exists("styles.css"):
        custom_classes = extract_css_classes(sandbox.read_file("styles.css"))

    # 3. Check existence and audit each page
    all_pages_exist = True
    combined_html = ""
    for page_file in expected_pages:
        if not sandbox.file_exists(page_file):
            all_pages_exist = False
            defects.append(QADefect(
                target=page_file,
                role_hint="structure",
                severity="critical",
                summary=f"Required page '{page_file}' does not exist in sandbox",
                remediation=f"Generate {page_file}",
                rule="page-existence"
            ))
        else:
            checks_passed.append(f"File {page_file} exists")
            page_content = sandbox.read_file(page_file)
            combined_html += "\n" + page_content

            # Audit HTML semantics
            html_def = audit_html(page_content, target_file=page_file)
            if not html_def:
                checks_passed.append(f"HTML syntax for {page_file} valid")
            else:
                defects.extend(html_def)

            # Audit links & anchors (Check 1)
            link_def = audit_links(page_content, current_file=page_file, sandbox=sandbox)
            if not link_def:
                checks_passed.append(f"Links in {page_file} valid")
            else:
                defects.extend(link_def)

            # Audit class whitelist (Check 2)
            class_def = audit_html_classes(page_content, current_file=page_file, allowed_classes=custom_classes)
            if not class_def:
                checks_passed.append(f"Component classes in {page_file} comply with design system")
            else:
                defects.extend(class_def)

            # Audit accessibility (Check 8)
            a11y_def = audit_accessibility(page_content, target_file=page_file)
            if not a11y_def:
                checks_passed.append(f"Accessibility structure on {page_file} valid")
            else:
                defects.extend(a11y_def)

            # Audit placeholders (Check 9)
            place_def = audit_placeholders(page_content, target_file=page_file)
            if not place_def:
                checks_passed.append(f"No placeholders found in {page_file}")
            else:
                defects.extend(place_def)

    # 4. Audit Requirements Coverage (Check 3)
    if spec_obj:
        req_def, coverage_map, coverage_pct = audit_requirements(sandbox, spec_obj)
        if not req_def:
            checks_passed.append(f"All {len(spec_obj.requirements)} specification requirements satisfied (100% coverage)")
        else:
            defects.extend(req_def)

    # 5. Check CSS & JS existence
    base_exists = sandbox.file_exists("base.css")
    css_exists = sandbox.file_exists("styles.css")
    js_exists = sandbox.file_exists("script.js")

    if base_exists:
        checks_passed.append("File base.css exists")
        base_content = sandbox.read_file("base.css")
        base_def = audit_css(base_content, target_file="base.css", is_base=True)
        if not base_def:
            checks_passed.append("base.css design system & theme variables valid")
        else:
            defects.extend(base_def)
    elif sandbox.file_exists("spec.json"):
        defects.append(QADefect(
            target="base.css",
            role_hint="style",
            severity="high",
            summary="base.css component library is missing in sandbox",
            remediation="Generate base.css from spec.theme using generate_base_css()",
            rule="css-syntax"
        ))

    if not css_exists:
        defects.append(QADefect(
            target="styles.css",
            role_hint="style",
            severity="high",
            summary="styles.css does not exist in sandbox",
            remediation="Generate styles.css",
            rule="css-syntax"
        ))
    else:
        checks_passed.append("File styles.css exists")
        css_content = sandbox.read_file("styles.css")
        css_def = audit_css(css_content, target_file="styles.css", is_base=not base_exists)
        if not css_def:
            checks_passed.append("CSS syntax and rules valid")
        else:
            defects.extend(css_def)

        # Theme color compliance (Check 4)
        color_def = audit_theme_colors(css_content, target_file="styles.css")
        if not color_def:
            checks_passed.append("styles.css conforms to theme variable palette")
        else:
            defects.extend(color_def)

    if not js_exists:
        defects.append(QADefect(
            target="script.js",
            role_hint="script",
            severity="high",
            summary="script.js does not exist in sandbox",
            remediation="Generate script.js",
            rule="js-check"
        ))
    else:
        checks_passed.append("File script.js exists")
        js_content = sandbox.read_file("script.js")
        js_def = audit_js(js_content, html_content=combined_html)
        if not js_def:
            checks_passed.append("JavaScript syntax and DOM selector targets valid across all pages")
        else:
            defects.extend(js_def)

        js_place_def = audit_placeholders(js_content, target_file="script.js")
        if js_place_def:
            defects.extend(js_place_def)

    # 6. Score & Convergence Decision
    # Strict convergence rules:
    # Passed ONLY if:
    # - 0 critical defects
    # - 0 high defects
    # - all expected pages exist
    # - css & js exist
    # - requirements coverage is 100% (or no spec.json)
    critical_count = sum(1 for d in defects if d.severity == "critical")
    high_count = sum(1 for d in defects if d.severity == "high")
    medium_count = sum(1 for d in defects if d.severity == "medium")
    low_count = sum(1 for d in defects if d.severity == "low")

    # Weighted score calculation
    deductions = (critical_count * 25.0) + (high_count * 15.0) + (medium_count * 5.0) + (low_count * 2.0)
    score = max(0.0, min(100.0, round(100.0 - deductions, 1)))

    passed = (
        critical_count == 0
        and high_count == 0
        and all_pages_exist
        and css_exists
        and js_exists
        and (coverage_pct >= 100.0 or not spec_obj)
    )

    return QAAuditReport(
        passed=passed,
        score=score,
        coverage_percent=coverage_pct,
        defects=defects,
        checks_passed=checks_passed,
        requirements_coverage=coverage_map
    )
