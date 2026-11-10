"""
Unit Tests for Phase 5 Real QA Suite (runtime/qa.py).
Tests:
1. Link check (resolves to spec page, anchor, or external; rejects '#' and empty)
2. Class check against base.css and custom styles
3. Requirements check (section IDs, features, R1..Rn mapping, coverage percentage)
4. Accessibility check (single h1, image alt, form labels)
5. Placeholder check (Lorem ipsum, TODO, empty href)
6. Convergence decision (only marked converged with 0 critical/high and 100% coverage)
"""

import sys
sys.path.insert(0, ".")

import json
import pytest
from runtime.sandbox import Sandbox
from runtime.spec import SiteSpec, PageSpec, SectionSpec, RequirementItem
from runtime.qa import (
    run_qa_audit,
    audit_links,
    audit_html_classes,
    audit_requirements,
    audit_accessibility,
    audit_placeholders,
    audit_theme_colors,
    audit_js
)


def test_link_check_rejects_placeholders_and_broken(tmp_path):
    sandbox = Sandbox("run_link_test", base_dir=str(tmp_path))
    sandbox.write_file("index.html", "<html></html>")

    # Content with placeholder '#' and non-existent page
    html = """
    <nav>
      <a href="#">Placeholder Link</a>
      <a href="nonexistent.html">Broken Link</a>
      <a href="#missing-section">Broken Anchor</a>
    </nav>
    <section id="existing-section">Content</section>
    <a href="#existing-section">Valid Anchor</a>
    <a href="https://example.com">Valid External</a>
    """

    defects = audit_links(html, "index.html", sandbox)
    assert len(defects) >= 3

    rules = [d.rule for d in defects]
    assert all(r == "link-check" for r in rules)

    summaries = [d.summary for d in defects]
    assert any("Placeholder or empty link" in s for s in summaries)
    assert any("nonexistent.html" in s for s in summaries)
    assert any("missing-section" in s for s in summaries)


def test_accessibility_checks():
    # 1. Multiple h1s and missing alt tag
    bad_html = """<!DOCTYPE html>
    <html>
      <head><title>Test</title></head>
      <body>
        <h1>Primary Headline</h1>
        <h1>Accidental Second Headline</h1>
        <img src="photo.jpg">
        <input type="text" id="username">
      </body>
    </html>"""

    defects = audit_accessibility(bad_html, "index.html")
    assert len(defects) >= 3

    summaries = [d.summary for d in defects]
    assert any("Multiple" in s and "<h1>" in s for s in summaries)
    assert any("alt attribute" in s for s in summaries)
    assert any("username" in s and "label" in s for s in summaries)

    # 2. Perfect accessibility
    good_html = """<!DOCTYPE html>
    <html>
      <head><title>Test</title></head>
      <body>
        <h1>Sole Primary Headline</h1>
        <h2>Section Heading</h2>
        <img src="photo.jpg" alt="Artisanal sourdough loaf">
        <label for="user-email">Email</label>
        <input type="email" id="user-email">
      </body>
    </html>"""

    good_defects = audit_accessibility(good_html, "index.html")
    assert len(good_defects) == 0


def test_placeholder_checks():
    dirty_html = """
    <div class="card">
      <h3>TODO: Add real pricing</h3>
      <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
    </div>
    """
    defects = audit_placeholders(dirty_html, "index.html")
    assert len(defects) >= 2
    summaries = [d.summary for d in defects]
    assert any("TODO" in s for s in summaries)
    assert any("Lorem ipsum" in s for s in summaries)


def test_requirements_mapping_and_coverage(tmp_path):
    sandbox = Sandbox("run_req_test", base_dir=str(tmp_path))

    spec = SiteSpec(
        site_type="restaurant",
        brand_name="Bakery",
        pages=[
            PageSpec(
                id="home",
                file="index.html",
                title="Home",
                sections=[
                    SectionSpec(id="hero", purpose="Headline", component="hero"),
                    SectionSpec(id="specials", purpose="Menu specials", component="card-grid")
                ]
            )
        ],
        features=["mobile-menu", "contact-form-validation"],
        requirements=[
            RequirementItem(id="R1", description="Display seasonal menu specials"),
            RequirementItem(id="R2", description="Provide interactive contact form")
        ]
    )

    # HTML missing section #specials and form
    partial_html = """
    <section id="hero"><h1>Bakery</h1></section>
    <div class="mobile-menu">Nav</div>
    """
    sandbox.write_file("index.html", partial_html)

    defects, coverage_map, pct = audit_requirements(sandbox, spec)
    assert len(defects) >= 1
    assert any("specials" in d.summary for d in defects)
    assert pct < 100.0


def test_full_qa_audit_strict_convergence(tmp_path):
    sandbox = Sandbox("run_converge_test", base_dir=str(tmp_path))

    # A complete site that satisfies all checks
    spec = SiteSpec(
        site_type="landing",
        brand_name="Nexus",
        tagline="Autonomous AI",
        pages=[
            PageSpec(
                id="home",
                file="index.html",
                title="Nexus | Home",
                sections=[
                    SectionSpec(id="hero", purpose="Hero", component="hero"),
                    SectionSpec(id="features", purpose="Features", component="card-grid")
                ]
            )
        ],
        features=["mobile-menu"],
        requirements=[
            RequirementItem(id="R1", description="Features section with fast speed")
        ]
    )

    from runtime.render import render_full_page
    from runtime.theme import generate_base_css

    sandbox.write_file("spec.json", spec.model_dump_json(indent=2))
    sandbox.write_file("base.css", generate_base_css(spec.theme))
    sandbox.write_file("styles.css", ".custom-accent { color: var(--accent); }")
    sandbox.write_file("script.js", "console.log('init');")

    main_markup = """
    <section id="hero" class="section hero">
      <div class="container hero-content">
        <h1 class="hero-title">Nexus AI</h1>
        <p class="hero-tagline">Autonomous generation</p>
        <div class="hero-actions">
          <a href="#features" class="btn btn-primary">Features</a>
        </div>
      </div>
    </section>
    <section id="features" class="section">
      <div class="container">
        <div class="grid grid-3">
          <div class="card"><h3 class="card-title">Fast speed performance</h3></div>
        </div>
      </div>
    </section>
    """

    full_html = render_full_page(spec, spec.pages[0], main_markup)
    sandbox.write_file("index.html", full_html)

    report = run_qa_audit(sandbox)
    assert report.passed is True, f"Expected clean pass, defects: {[d.summary for d in report.defects]}"
    assert report.score >= 90.0
    assert report.coverage_percent == 100.0
