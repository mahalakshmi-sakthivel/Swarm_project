"""
Unit tests for Stage 2 Automated QA Engine.
"""

import sys
sys.path.insert(0, ".")

import pytest
from runtime.sandbox import Sandbox
from runtime.qa import run_qa_audit, audit_html, audit_css, audit_js


def test_qa_detects_missing_assets(tmp_path):
    sandbox = Sandbox("run_test_missing", base_dir=str(tmp_path))
    # Empty sandbox
    report = run_qa_audit(sandbox)
    assert report.passed is False
    assert len(report.defects) >= 3

    targets = [d.target for d in report.defects]
    assert "index.html" in targets
    assert "styles.css" in targets
    assert "script.js" in targets


def test_qa_detects_html_defects():
    bad_html = "<html><body><h1>No Doctype and no head</h1></body></html>"
    defects = audit_html(bad_html)
    summaries = [d.summary for d in defects]

    assert any("DOCTYPE" in s for s in summaries)
    assert any("head" in s for s in summaries)
    assert any("styles.css" in s for s in summaries)


def test_qa_detects_css_unbalanced_braces():
    bad_css = "body { color: red; "
    defects = audit_css(bad_css)
    assert len(defects) >= 1
    assert any("Unbalanced" in d.summary for d in defects)


def test_qa_detects_js_unmatched_selector():
    html = '<div class="btn-primary">Click me</div>'
    bad_js = 'document.querySelector(".non-existent-modal").addEventListener("click", () => {});'
    defects = audit_js(bad_js, html_content=html)
    assert len(defects) >= 1
    assert any("non-existent-modal" in d.summary for d in defects)


def test_qa_passes_valid_project(tmp_path):
    sandbox = Sandbox("run_test_pass", base_dir=str(tmp_path))
    sandbox.write_file(
        "index.html",
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Valid Site</title>
  <link rel="stylesheet" href="styles.css">
  <script src="script.js" defer></script>
</head>
<body>
  <button class="mobile-menu-btn">Menu</button>
  <nav class="nav-links"></nav>
</body>
</html>"""
    )
    sandbox.write_file(
        "styles.css",
        """:root { --bg-primary: #111; }
body { background: var(--bg-primary); }
@media (max-width: 768px) { body { font-size: 14px; } }"""
    )
    sandbox.write_file(
        "script.js",
        """const btn = document.querySelector('.mobile-menu-btn');
if (btn) { btn.addEventListener('click', () => {}); }"""
    )

    report = run_qa_audit(sandbox)
    assert report.passed is True
    assert report.score == 100.0
    assert len(report.defects) == 0

