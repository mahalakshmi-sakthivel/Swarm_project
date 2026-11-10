"""
Unit Tests for Phase 6: Smaller Reliable LLM Calls, Content Agent, Model Config & HTML Healer.
"""

import pytest
from runtime.healer import heal_html_markup, HTMLTagHealer
from runtime.llm import ModelConfig, QwenClient
from runtime.roles import ALL_ROLES, ROLE_CONTENT, get_role_by_hint
from runtime.content import generate_default_copy, SiteCopy, PageCopy, _resolve_tone_preset
from runtime.spec import SiteSpec, PageSpec, SectionSpec, ThemeSpec


# ---------------------------------------------------------
# Test 1: HTML Parser-Based Markup Healer
# ---------------------------------------------------------

def test_healer_closes_single_unclosed_tag():
    raw = "<div>Hello World"
    healed = heal_html_markup(raw)
    assert healed == "<div>Hello World</div>"


def test_healer_closes_nested_unclosed_tags():
    raw = '<div class="container"><section class="hero"><h1>Headline</h1><p>Paragraph text'
    healed = heal_html_markup(raw)
    assert healed == '<div class="container"><section class="hero"><h1>Headline</h1><p>Paragraph text</p></section></div>'


def test_healer_repairs_improperly_nested_or_missing_inner_close():
    raw = '<div class="card"><p>Card body content without closing p tag</div>'
    healed = heal_html_markup(raw)
    assert healed == '<div class="card"><p>Card body content without closing p tag</p></div>'


def test_healer_preserves_html5_void_elements():
    raw = '<section><img src="hero.jpg" alt="Hero image"><br><hr><input type="text" name="email"></section>'
    healed = heal_html_markup(raw)
    assert "</img>" not in healed
    assert "</input>" not in healed
    assert "</br>" not in healed
    assert "</hr>" not in healed
    assert healed == '<section><img src="hero.jpg" alt="Hero image"><br><hr><input type="text" name="email"></section>'


def test_healer_handles_empty_or_whitespace_safely():
    assert heal_html_markup("") == ""
    assert heal_html_markup("   ") == "   "
    assert heal_html_markup(None) is None


# ---------------------------------------------------------
# Test 2: Model Configuration & Swappable Model
# ---------------------------------------------------------

def test_model_config_defaults():
    config = ModelConfig()
    assert config.model_name in ("qwen3.5:4b", "qwen2.5-coder:7b")
    assert config.code_temperature == 0.2
    assert config.copy_temperature == 0.6
    assert config.num_predict == 2048


def test_client_model_hot_swapping():
    client = QwenClient(model="qwen3.5:4b")
    assert client.model == "qwen3.5:4b"

    client.set_model("qwen2.5-coder:7b")
    assert client.model == "qwen2.5-coder:7b"
    assert client.config.model_name == "qwen2.5-coder:7b"


# ---------------------------------------------------------
# Test 3: LLM Telemetry & Throughput Tracking
# ---------------------------------------------------------

def test_client_telemetry_tracking():
    client = QwenClient(model="qwen3.5:4b")

    # Manually register telemetry records
    client.record_agent_failure("agent-structure-01")
    assert client.agent_telemetry["agent-structure-01"]["failed_calls"] == 1

    summary = client.get_telemetry_summary()
    assert summary["model"] == "qwen3.5:4b"
    assert "agent-structure-01" in summary["agents"]
    assert summary["agents"]["agent-structure-01"]["failed_calls"] == 1


# ---------------------------------------------------------
# Test 4: Content Copywriter Agent Role Definition
# ---------------------------------------------------------

def test_role_content_definition():
    assert "content" in ALL_ROLES
    assert ROLE_CONTENT.name == "content"
    assert ROLE_CONTENT.default_agent_id == "agent-content-01"
    assert "copy.json" in ROLE_CONTENT.target_files

    matched = get_role_by_hint("copywriter")
    assert matched is not None
    assert matched.name == "content"

    matched_alias = get_role_by_hint("copy")
    assert matched_alias.name == "content"


# ---------------------------------------------------------
# Test 5: Tone-Matched Zero-Placeholder Copy Generation
# ---------------------------------------------------------

def test_content_generation_zero_placeholders():
    spec = SiteSpec(
        site_type="restaurant",
        brand_name="Bistro Lumiere",
        tagline="Artisan French dining in the heart of the city",
        tone="elegant",
        pages=[
            PageSpec(
                id="index",
                file="index.html",
                title="Home",
                sections=[
                    SectionSpec(id="hero", purpose="introduction", component="hero"),
                    SectionSpec(id="menu", purpose="featured dishes", component="grid"),
                    SectionSpec(id="contact", purpose="reservations", component="form")
                ]
            ),
            PageSpec(
                id="menu",
                file="menu.html",
                title="Menu",
                sections=[
                    SectionSpec(id="dishes", purpose="full seasonal menu", component="grid")
                ]
            )
        ]
    )

    copy: SiteCopy = generate_default_copy(spec)

    assert copy.brand_name == "Bistro Lumiere"
    assert len(copy.pages) == 2
    assert copy.pages[0].headline != ""
    assert "Lorem ipsum" not in copy.pages[0].headline
    assert "TODO" not in copy.pages[0].headline
    assert "Your text here" not in copy.pages[0].headline

    hero_sec = copy.pages[0].sections.get("hero")
    assert hero_sec is not None
    assert "Bistro Lumiere" in hero_sec.title
    assert hero_sec.cta != ""


def test_tone_preset_differentiation():
    playful = _resolve_tone_preset("playful")
    elegant = _resolve_tone_preset("elegant")
    bold = _resolve_tone_preset("bold")

    assert playful["cta_primary"] != elegant["cta_primary"]
    assert bold["cta_primary"] != playful["cta_primary"]
    assert "craft" in elegant["hero_prefix"] or "bespoke" in elegant["contact_subtitle"]
