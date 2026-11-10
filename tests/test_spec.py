"""
Unit Tests for Phase 1 SiteSpec Contract (runtime/spec.py).
Tests:
1. Pydantic validation and schema serialization
2. Domain-specific default spec generation (portfolio, restaurant/bakery, SaaS)
3. Multi-page layout inference from prompt keywords
4. Deterministic theme generation (mood, primary, secondary, bg, text, radius)
5. Graceful parsing and healing of partial or malformed LLM outputs
"""

import json
import pytest
from runtime.spec import (
    SiteSpec,
    PageSpec,
    SectionSpec,
    ThemeSpec,
    generate_default_spec,
    parse_or_repair_spec,
    detect_site_type
)


def test_site_spec_validation():
    """Verify that a complete SiteSpec serializes and deserializes accurately."""
    spec = SiteSpec(
        site_type="restaurant",
        brand_name="Le Petit Bistro",
        tagline="Authentic French Cuisine",
        audience="Foodies & diners",
        tone="warm & elegant",
        pages=[
            PageSpec(
                id="home",
                file="index.html",
                title="Home | Le Petit Bistro",
                sections=[
                    SectionSpec(id="hero", purpose="Welcome & reservation CTA", component="hero"),
                    SectionSpec(id="specials", purpose="Chef specials", component="card-grid")
                ]
            )
        ],
        nav=["home"],
        theme=ThemeSpec(
            mood="warm",
            primary="#d97706",
            secondary="#78350f",
            accent="#f59e0b",
            bg="#fdfbf7",
            text="#1c1917",
            dark_mode=False
        ),
        features=["mobile-menu", "contact-form-validation"],
        assumptions=["Inferred French culinary theme from prompt"]
    )

    json_str = spec.model_dump_json(indent=2)
    reloaded = SiteSpec.model_validate_json(json_str)

    assert reloaded.site_type == "restaurant"
    assert reloaded.brand_name == "Le Petit Bistro"
    assert len(reloaded.pages) == 1
    assert reloaded.pages[0].sections[0].id == "hero"
    assert reloaded.theme.primary == "#d97706"
    assert reloaded.theme.dark_mode is False


def test_detect_site_type():
    assert detect_site_type("Build a developer portfolio with my GitHub projects") == "portfolio"
    assert detect_site_type("Rustic sourdough bakery website with menu") == "restaurant"
    assert detect_site_type("Modern AI analytics SaaS platform with pricing") == "saas"
    assert detect_site_type("Online boutique clothing store") == "store"
    assert detect_site_type("Tech blog with daily AI articles") == "blog"


def test_generate_default_spec_multipage_bakery():
    prompt = "Create a rustic bakery website with 3 pages: Home with seasonal specials, Menu with prices and categories, and About Us with our story and contact form."
    spec = generate_default_spec(prompt)

    assert spec.site_type == "restaurant"
    assert len(spec.pages) == 3
    assert [p.file for p in spec.pages] == ["index.html", "menu.html", "about.html"]
    assert spec.nav == ["home", "menu", "about"]
    assert len(spec.requirements) >= 4
    # Restaurant defaults to warm light mode unless dark mode explicitly requested
    assert spec.theme.dark_mode is False
    assert len(spec.assumptions) > 0


def test_generate_default_spec_saas_dark_mode():
    prompt = "Build a modern developer observability SaaS platform with dark theme"
    spec = generate_default_spec(prompt)

    assert spec.site_type == "saas"
    assert spec.theme.dark_mode is True
    assert spec.theme.primary.startswith("#")
    assert spec.theme.accent.startswith("#")
    assert len(spec.pages) >= 1
    assert "mobile-menu" in spec.features


def test_parse_or_repair_spec_fallback():
    prompt = "Build a portfolio website"

    # 1. Invalid input returns full default spec
    spec1 = parse_or_repair_spec(None, prompt)
    assert spec1.site_type == "portfolio"
    assert len(spec1.pages) >= 1

    # 2. Corrupt string input returns default spec
    spec2 = parse_or_repair_spec("invalid json {", prompt)
    assert spec2.site_type == "portfolio"

    # 3. Partial dict input is gracefully merged with default spec
    partial = {
        "brand_name": "Custom Studio",
        "tagline": "Customized Tagline",
        "theme": {"primary": "#ff0077"}
    }
    spec3 = parse_or_repair_spec(partial, prompt)
    assert spec3.brand_name == "Custom Studio"
    assert spec3.tagline == "Customized Tagline"
    assert spec3.theme.primary == "#ff0077"
    assert len(spec3.pages) >= 1  # pages filled from defaults
