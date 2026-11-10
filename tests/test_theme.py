"""
Unit Tests for Phase 3 Deterministic Theme System & Component Library.
Verifies:
1. :root CSS generation from ThemeSpec
2. Comprehensive base.css component library (.container, .hero, .grid, .card, .btn, etc.)
3. Google Fonts link generation
4. QA checks for theme color compliance and design system classes
"""

import sys
sys.path.insert(0, ".")

import pytest
from runtime.spec import ThemeSpec
from runtime.theme import (
    generate_root_css,
    generate_base_css,
    get_google_fonts_link,
    ALLOWED_COMPONENT_CLASSES,
    ALLOWED_COMPONENT_CLASSES_SET
)
from runtime.qa import audit_css, audit_theme_colors, audit_html_classes


def test_generate_root_css():
    theme = ThemeSpec(
        mood="cyberpunk",
        primary="#06b6d4",
        secondary="#475569",
        accent="#f43f5e",
        bg="#090d16",
        bg_surface="#111827",
        text="#f8fafc",
        text_muted="#94a3b8",
        font_heading="Outfit, sans-serif",
        font_body="Inter, sans-serif",
        radius="12px",
        shadow="0 10px 30px rgba(0,0,0,0.5)",
        dark_mode=True
    )

    root_css = generate_root_css(theme)
    assert ":root {" in root_css
    assert "--primary: #06b6d4;" in root_css
    assert "--accent: #f43f5e;" in root_css
    assert "--bg-primary: #090d16;" in root_css
    assert "--font-heading: Outfit, sans-serif;" in root_css
    assert "--radius: 12px;" in root_css
    assert "--radius-sm: 6px;" in root_css
    assert "--radius-lg: 24px;" in root_css
    assert "--primary-rgb:" in root_css


def test_generate_base_css_components_and_braces():
    theme = ThemeSpec(mood="modern", primary="#2563eb", accent="#06b6d4")
    base_css = generate_base_css(theme)

    # Braces balance
    assert base_css.count("{") == base_css.count("}")
    assert base_css.count("{") >= 20

    # Core required components
    required_selectors = [
        ":root",
        ".container",
        ".section",
        ".hero",
        ".grid",
        ".grid-2",
        ".grid-3",
        ".grid-4",
        ".card",
        ".btn",
        ".btn-primary",
        ".btn-outline",
        ".badge",
        ".form",
        ".testimonial",
        ".pricing",
        ".gallery",
        ".faq",
        ".stats",
        ".navbar",
        ".site-footer",
        "@media (max-width: 768px)"
    ]

    for sel in required_selectors:
        assert sel in base_css, f"Expected selector '{sel}' in base.css"

    # Accessible focus states
    assert ":focus-visible" in base_css


def test_google_fonts_link_generation():
    # Recognized fonts
    link_html = get_google_fonts_link("Playfair Display, serif", "Inter, sans-serif")
    assert "fonts.googleapis.com" in link_html
    assert "Playfair+Display" in link_html
    assert "Inter" in link_html

    # Standard system fonts (no link generated)
    sys_link = get_google_fonts_link("system-ui, sans-serif", "Arial, sans-serif")
    assert sys_link == ""


def test_qa_theme_colors_compliance():
    # Compliant CSS using variables
    clean_css = """
    .custom-hero {
      background: var(--bg-surface);
      color: var(--text-primary);
      border: 1px solid var(--border-color);
    }
    """
    defects = audit_theme_colors(clean_css)
    assert len(defects) == 0

    # Non-compliant CSS with hardcoded hex colors
    dirty_css = """
    .custom-hero {
      background: #ff0055;
      color: #123456;
    }
    """
    dirty_defects = audit_theme_colors(dirty_css)
    assert len(dirty_defects) >= 1
    summaries = [d.summary for d in dirty_defects]
    assert any("#ff0055" in s or "#123456" in s for s in summaries)


def test_qa_html_classes_compliance():
    # Compliant HTML
    good_html = """
    <div class="container section">
      <div class="hero">
        <h1 class="hero-title">Hello</h1>
        <div class="hero-actions">
          <a href="#" class="btn btn-primary">Start</a>
        </div>
      </div>
      <div class="grid grid-3">
        <div class="card"><h3 class="card-title">Feature</h3></div>
      </div>
    </div>
    """
    defects = audit_html_classes(good_html, "index.html")
    assert len(defects) == 0

    # HTML with rogue unstyled class
    rogue_html = '<div class="container"><div class="rogue-mystery-wrapper-xyz">Content</div></div>'
    defects_rogue = audit_html_classes(rogue_html, "index.html")
    assert len(defects_rogue) == 1
    assert "rogue-mystery-wrapper-xyz" in defects_rogue[0].summary

