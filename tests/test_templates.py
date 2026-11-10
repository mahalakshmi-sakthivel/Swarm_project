"""
Unit Tests for Phase 4 Templates System (runtime/templates.py).
Tests:
1. Loading starter templates across all site types (restaurant, saas, portfolio, store, blog, landing)
2. Multi-page starter template resolution
3. Template placeholder hydration (brand_name, tagline)
4. Few-shot example retrieval
5. Strict 100% compliance of all templates with ALLOWED_COMPONENT_CLASSES in base.css
"""

import sys
sys.path.insert(0, ".")

import pytest
from runtime.spec import SiteSpec, PageSpec
from runtime.templates import (
    load_starter_template,
    fill_template_placeholders,
    get_few_shot_example,
    TEMPLATES_DIR
)
from runtime.qa import audit_html_classes


@pytest.mark.parametrize("site_type", ["restaurant", "saas", "portfolio", "store", "blog", "landing"])
def test_starter_templates_exist_and_load(site_type):
    tmpl = load_starter_template(site_type, "index.html")
    assert tmpl is not None, f"Template for {site_type}/index.html must exist"
    assert len(tmpl) > 100
    assert "class=\"container" in tmpl or "class=\"section" in tmpl
    assert "class=\"hero" in tmpl or "class=\"card" in tmpl


def test_restaurant_multipage_templates():
    menu_tmpl = load_starter_template("restaurant", "menu.html")
    assert menu_tmpl is not None
    assert "Burrata" in menu_tmpl or "Signature Entrees" in menu_tmpl

    about_tmpl = load_starter_template("restaurant", "about.html")
    assert about_tmpl is not None
    assert "reservation-form" in about_tmpl
    assert "Book a Table" in about_tmpl


def test_fill_template_placeholders():
    spec = SiteSpec(
        site_type="restaurant",
        brand_name="Artisanal Hearth",
        tagline="Naturally fermented breads & wood-fired cuisine"
    )
    page = PageSpec(id="home", file="index.html", title="Home", sections=[])

    raw = '<h1 class="hero-title">{{ brand_name }}</h1><p class="hero-tagline">{{ tagline }}</p>'
    hydrated = fill_template_placeholders(raw, spec, page)

    assert "Artisanal Hearth" in hydrated
    assert "Naturally fermented breads & wood-fired cuisine" in hydrated
    assert "{{" not in hydrated


@pytest.mark.parametrize("site_type", ["restaurant", "saas", "portfolio", "store", "blog", "landing"])
def test_few_shot_examples_valid(site_type):
    few_shot = get_few_shot_example(site_type)
    assert few_shot is not None
    assert len(few_shot) > 100
    assert "class=\"hero" in few_shot
    assert "class=\"card" in few_shot
    # Check that it's clean section markup, not full html doc
    assert "<!DOCTYPE" not in few_shot
    assert "<body" not in few_shot


def test_all_starter_templates_comply_with_base_css_classes():
    """Verify that every single HTML file in /templates uses only allowed design system classes."""
    html_files = list(TEMPLATES_DIR.glob("**/*.html"))
    assert len(html_files) >= 6, f"Expected at least 6 template files, found {len(html_files)}"

    for html_file in html_files:
        content = html_file.read_text(encoding="utf-8")
        defects = audit_html_classes(content, html_file.name)
        assert len(defects) == 0, f"Template {html_file.relative_to(TEMPLATES_DIR)} has unallowed classes: {[d.summary for d in defects]}"
