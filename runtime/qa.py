"""
QA Engine - Automated Verification & Defect Detection for Stage 2.
Performs deterministic audits of HTML, CSS, and JS assets in the sandbox.
Reports defects with targeted role hints for automated repair loops.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional
from runtime.sandbox import Sandbox
from runtime.theme import ALLOWED_COMPONENT_CLASSES_SET


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


def audit_html(content: str, target_file: str = "index.html") -> List[QADefect]:
    defects = []

    if "<!DOCTYPE HTML>" not in content.upper():
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="critical",
            summary=f"Missing <!DOCTYPE html> declaration in {target_file}",
            remediation=f"Add <!DOCTYPE html> as the very first line of {target_file}"
        ))

    if "<html" not in content or "</html>" not in content:
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="critical",
            summary=f"Missing <html> or </html> tags in {target_file}",
            remediation="Wrap the document in <html lang=\"en\"> ... </html>"
        ))

    if "<head>" not in content or "</head>" not in content:
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="critical",
            summary=f"Missing <head> section in {target_file}",
            remediation="Include a valid <head> element with meta charset, viewport, and title"
        ))

    if "viewport" not in content:
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="medium",
            summary=f"Missing responsive viewport meta tag in {target_file}",
            remediation="Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
        ))

    if 'href="styles.css"' not in content and "href='styles.css'" not in content:
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="high",
            summary=f"styles.css is not linked in {target_file}",
            remediation="Add <link rel=\"stylesheet\" href=\"styles.css\"> inside <head>"
        ))

    if "script.js" not in content:
        defects.append(QADefect(
            target=target_file,
            role_hint="structure",
            severity="high",
            summary=f"script.js is not referenced in {target_file}",
            remediation="Add <script src=\"script.js\" defer></script>"
        ))

    return defects


def audit_links(content: str, current_file: str, sandbox: Sandbox) -> List[QADefect]:
    """Deterministic link check: verifies every <a href> points to a valid file or anchor."""
    defects = []
    hrefs = re.findall(r'href=[\'"]([^\'"]+)[\'"]', content)
    for href in hrefs:
        href_clean = href.strip()
        if not href_clean or href_clean == "#":
            defects.append(QADefect(
                target=current_file,
                role_hint="structure",
                severity="medium",
                summary=f"Placeholder or empty link '{href}' found in {current_file}",
                remediation="Point link to a valid relative page (e.g. index.html) or section anchor"
            ))
            continue

        if href_clean.startswith(("http://", "https://", "mailto:", "tel:", "javascript:")):
            continue

        # Relative link
        parts = href_clean.split("#")
        target_page = parts[0]
        anchor = parts[1] if len(parts) > 1 else ""

        if target_page:
            if not sandbox.file_exists(target_page):
                defects.append(QADefect(
                    target=current_file,
                    role_hint="structure",
                    severity="critical",
                    summary=f"Broken link in {current_file}: '{href_clean}' targets nonexistent page '{target_page}'",
                    remediation=f"Ensure {target_page} is generated or update href"
                ))
        elif anchor:
            # Same-page anchor
            if f'id="{anchor}"' not in content and f"id='{anchor}'" not in content:
                defects.append(QADefect(
                    target=current_file,
                    role_hint="structure",
                    severity="medium",
                    summary=f"Anchor link '#{anchor}' in {current_file} does not match any id in the page",
                    remediation=f"Add id=\"{anchor}\" to the target section in {current_file}"
                ))

    return defects


def audit_html_classes(content: str, current_file: str) -> List[QADefect]:
    """Check that classes used in HTML belong to base.css design system or structural patterns."""
    defects = []
    class_attrs = re.findall(r'class=[\'"]([^\'"]+)[\'"]', content)
    for class_str in class_attrs:
        classes = class_str.strip().split()
        for cls in classes:
            cls_clean = cls.strip()
            if not cls_clean:
                continue
            # Allow defined component classes and standard dynamic/framework patterns
            if (
                cls_clean in ALLOWED_COMPONENT_CLASSES_SET
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
                remediation=f"Use standard design system component classes from base.css instead of '{cls_clean}'"
            ))
    return defects


def audit_theme_colors(css_content: str, target_file: str = "styles.css") -> List[QADefect]:
    """Verify that CSS does not use hardcoded hex colors outside :root."""
    defects = []
    clean_css = re.sub(r'/\*[\s\S]*?\*/', '', css_content)
    # Exclude :root block from check
    non_root_css = re.sub(r':root\s*\{[\s\S]*?\}', '', clean_css)
    
    hex_matches = re.findall(r'#(?:[0-9a-fA-F]{3,8})\b', non_root_css)
    unique_hexes = list(set(hex_matches))
    for h in unique_hexes[:3]:
        defects.append(QADefect(
            target=target_file,
            role_hint="style",
            severity="medium",
            summary=f"Hardcoded hex color '{h}' found in {target_file}",
            remediation=f"Replace '{h}' with theme CSS variables: var(--primary), var(--accent), var(--bg-surface), etc."
        ))
    return defects


def audit_css(content: str, target_file: str = "styles.css", is_base: bool = False) -> List[QADefect]:
    defects = []

    clean_content = content.strip()

    if len(clean_content) < 15:
        defects.append(QADefect(
            target=target_file,
            role_hint="style",
            severity="critical",
            summary=f"{target_file} is too short ({len(clean_content)} bytes) or empty",
            remediation=f"Generate a functional stylesheet in {target_file}"
        ))

    if clean_content.startswith("<!--") or ("/* CSS" in clean_content and len(clean_content) < 120):
        defects.append(QADefect(
            target=target_file,
            role_hint="style",
            severity="critical",
            summary=f"{target_file} contains placeholder comment stubs instead of functional CSS rules",
            remediation="Provide complete CSS declarations for all navigation, hero, card, and footer classes"
        ))

    if "<!DOCTYPE" in content.upper() or "<HTML" in content.upper() or "<STYLE" in content.upper():
        defects.append(QADefect(
            target=target_file,
            role_hint="style",
            severity="critical",
            summary=f"{target_file} contains HTML markup instead of CSS rules",
            remediation=f"{target_file} must contain only pure CSS stylesheet rules, not HTML tags"
        ))

    open_braces = content.count("{")
    close_braces = content.count("}")

    if open_braces != close_braces:
        defects.append(QADefect(
            target=target_file,
            role_hint="style",
            severity="critical",
            summary=f"Unbalanced CSS braces in {target_file} ({open_braces} open vs {close_braces} close)",
            remediation=f"Fix mismatched curly braces in {target_file}"
        ))

    if open_braces == 0:
        defects.append(QADefect(
            target=target_file,
            role_hint="style",
            severity="critical",
            summary=f"{target_file} lacks rule blocks (no '{{' braces found)",
            remediation=f"Implement styling rule blocks for HTML elements and classes in {target_file}"
        ))

    if is_base:
        if ":root" not in content and "--" not in content:
            defects.append(QADefect(
                target=target_file,
                role_hint="style",
                severity="high",
                summary=f"Missing :root block in {target_file}",
                remediation="Define theme variables in a :root block (e.g., --bg-primary, --text-primary)"
            ))

        if "@media" not in content:
            defects.append(QADefect(
                target=target_file,
                role_hint="style",
                severity="medium",
                summary=f"No media queries detected in {target_file} for responsive design",
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
    """Execute full automated QA verification suite against sandbox workspace across all pages."""
    defects: List[QADefect] = []
    checks_passed: List[str] = []

    # 1. Determine expected pages from spec.json if available
    expected_pages = ["index.html"]
    if sandbox.file_exists("spec.json"):
        try:
            import json
            spec_raw = json.loads(sandbox.read_file("spec.json"))
            if "pages" in spec_raw and isinstance(spec_raw["pages"], list):
                expected_pages = [p.get("file", f"{p.get('id', 'page')}.html") for p in spec_raw["pages"] if isinstance(p, dict)]
                if not expected_pages:
                    expected_pages = ["index.html"]
        except Exception:
            expected_pages = ["index.html"]

    # Also discover any extra .html files in sandbox
    for f in sandbox.list_files():
        if f.endswith(".html") and f not in expected_pages:
            expected_pages.append(f)

    # 2. Check existence of expected pages
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
                remediation=f"Generate {page_file}"
            ))
        else:
            checks_passed.append(f"File {page_file} exists")
            page_content = sandbox.read_file(page_file)
            combined_html += "\n" + page_content
            
            # Audit HTML semantics
            html_def = audit_html(page_content, target_file=page_file)
            if not html_def:
                checks_passed.append(f"HTML structure for {page_file} valid")
            else:
                defects.extend(html_def)

            # Audit relative links & anchor links
            link_def = audit_links(page_content, current_file=page_file, sandbox=sandbox)
            if not link_def:
                checks_passed.append(f"Links in {page_file} valid")
            else:
                defects.extend(link_def)

            # Audit design system component classes compliance (Phase 3)
            class_def = audit_html_classes(page_content, current_file=page_file)
            if not class_def:
                checks_passed.append(f"Component classes in {page_file} comply with design system")
            else:
                defects.extend(class_def)

    # 3. Check CSS & JS existence
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
            remediation="Generate base.css from spec.theme using generate_base_css()"
        ))

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
        css_content = sandbox.read_file("styles.css")
        css_def = audit_css(css_content, target_file="styles.css", is_base=not base_exists)
        if not css_def:
            checks_passed.append("CSS syntax and rules valid")
        else:
            defects.extend(css_def)

        # Check theme color compliance (no hardcoded colors outside :root)
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
            remediation="Generate script.js"
        ))
    else:
        checks_passed.append("File script.js exists")
        js_content = sandbox.read_file("script.js")
        js_def = audit_js(js_content, html_content=combined_html)
        if not js_def:
            checks_passed.append("JavaScript syntax and DOM selector links valid across all pages")
        else:
            defects.extend(js_def)

    critical_count = sum(1 for d in defects if d.severity in ("critical", "high"))
    score = max(0.0, 100.0 - (len(defects) * 15.0))
    passed = (critical_count == 0) and all_pages_exist and css_exists and js_exists

    return QAAuditReport(
        passed=passed,
        score=score,
        defects=defects,
        checks_passed=checks_passed
    )
