# Changelog

All notable changes to the Swarm Website Builder project will be documented in this file.

## [Phase 6: Smaller Reliable LLM Calls, Content Agent, Model Config & HTML Healer] - 2026-11-10
### Added
- `runtime/healer.py`:
  - Zero-dependency `HTMLTagHealer` and `heal_html_markup(raw_html)` based on Python's built-in `html.parser.HTMLParser`.
  - Automatically balances and closes unclosed HTML tags in LIFO order while preserving void tags (`<img>`, `<input>`, `<br>`, `<meta>`, `<link>`) without invalid closing tags.
- `runtime/content.py`:
  - `SiteCopy`, `PageCopy`, and `PageSectionCopy` models for structured, authentic marketing and UI copywriting.
  - `generate_default_copy(spec: SiteSpec)`: Tone-tailored copy synthesizer (playful, elegant, bold, professional) guaranteeing zero placeholder text, zero "Lorem ipsum", and zero "TODO" tags.
  - Integration with `task-00-plan` and the new Content Agent to record `copy.json` in the sandbox as a shared artifact.
- `ROLE_CONTENT` in `runtime/roles.py`:
  - New 6th specialized peer agent: Content Copywriting Specialist (`agent-content-01`).
  - Specialized system prompt strictly forbidding placeholders and mandating tone-tailored copy.
  - Added to `ALL_ROLES` and `ROLE_ALIASES`.
- `ModelConfig` and LLM Telemetry in `runtime/llm.py`:
  - `ModelConfig` dataclass with swappable model support (`DEFAULT_MODEL="qwen3.5:4b"`, fallback `FALLBACK_MODEL="qwen2.5-coder:7b"`), code temperature (0.2), and copywriting temperature (0.6).
  - `set_model(model_name)`: Dynamic model hot swapping.
  - Real-time token throughput tracking (`tokens_per_sec = eval_count / (eval_duration / 1e9)`), latency logging, and per-agent failure counters (`agent_telemetry`).
  - `get_telemetry_summary()`: Aggregated telemetry for dashboard and reporting.
- Prompt token budgeting in `runtime/agent.py`:
  - Keeps prompts strictly under ~1500 tokens for local 4B model reliability.
  - Replaces massive raw HTML file dumps with concise DOM selector outlines (`#id` inventory and class lists) for style and script specialists.
  - Injects `copy_context` from `copy.json` into structure prompts.
- `tests/test_phase6.py`: 11 unit tests verifying HTML tag healing, void element preservation, model configuration, telemetry metrics, `ROLE_CONTENT` registration, and tone-matched copy generation.

### Changed
- `runtime/render.py`: Automatically runs `heal_html_markup` on `<main>` content before page assembly.
- `runtime/swarm.py`: Added `ROLE_CONTENT` to the concurrent multi-agent worker set.
- `tests/test_stage2_roles.py`: Updated tests to verify all 6 swarm roles and aliases.

---

## [Phase 5: Real Deterministic QA Suite & Strict Convergence] - 2026-11-10
### Added
- Complete rewrite of `runtime/qa.py` with 9 deterministic rules producing structured defect records (`{target, line, rule, severity, summary, remediation, req_id}`):
  1. **Link Check (`link-check`)**: Verifies every `<a href>` resolves to an existing file in the sandbox, an anchor `#id` on the target page, or an external URL. Explicitly flags empty `#` placeholders and dead links with line numbers.
  2. **Class Check (`class-check`)**: Validates every class against `base.css` whitelist, `styles.css` classes, and dynamic structural patterns.
  3. **Requirements Check (`requirements-check`)**: Validates that all page section IDs exist in HTML, all `spec.features` have corresponding markup or JS handlers, maps back to requirement IDs (R1..Rn), and computes live requirement coverage percentage.
  4. **Theme Check (`theme-check`)**: Enforces variable usage; rejects hardcoded hex colors (`#[0-9a-fA-F]{3,8}`) and unauthorized fonts outside `:root`.
  5. **JS Check (`js-check`)**: Validates bracket balance (`{}`, `()`, `[]`) and verifies that all `getElementById` and `querySelector` targets exist in the combined HTML.
  6. **Accessibility Check (`accessibility-check`)**: Enforces exactly one `<h1>` per page, non-empty `alt` attributes on all images, and explicit `<label for="...">` or `aria-label` associations on form inputs.
  7. **Placeholder Check (`placeholder-check`)**: Rejects `"Lorem ipsum"`, `"TODO"`, `"FIXME"`, `"Your text here"`, and empty hrefs with line numbers.
  8. **Responsive Check (`responsive-check`)**: Verifies responsive viewport meta tags, `@media` breakpoints, and fluid grid layouts.
  9. **Strict Convergence Decision**: A run is ONLY marked "converged" when checks 1–6 have zero critical or high errors and requirement coverage is 100%.
- Maximum 3 repair cycles limit in `runtime/agent.py` and `runtime/swarm.py`: if actionable defects remain after 3 fix iterations, the swarm honestly marks the run as `"partial"` rather than marking broken sites as converged.
- `tests/test_qa_phase5.py`: 5 comprehensive unit tests verifying link check rejections, accessibility rules, placeholder detection, requirement mapping, and strict convergence criteria.

---

## [Phase 4: Templates per Site Type & Few-Shot Prompts] - 2026-11-10
### Added
- Curated `/templates` directory with hand-crafted starter layout templates across all primary site types:
  - `templates/restaurant/`: `index.html` (hero, seasonal specials grid, culinary philosophy), `menu.html` (appetizers, wood-fired mains, pricing), `about.html` (kitchen craft, chef quote, interactive reservation form).
  - `templates/saas/`: `index.html` (platform hero, live stats counter bar, grid-3 feature showcase, 3-tier pricing matrix, architecture review inquiry form).
  - `templates/portfolio/`: `index.html` (design & engineering intro hero, selected project cards with tags, skills grid, contact form), `work.html` (detailed case study cards with measurable metrics).
  - `templates/store/`: `index.html` (promo banner hero, curated trending products grid with prices and 'Add to Bag' actions, carbon-neutral trust badges).
  - `templates/blog/`: `index.html` (thoughtful essays hero, editor's pick 3-column articles grid with reading times, newsletter signup).
  - `templates/landing/`: `index.html` (high-conversion hero, 3-step workflow grid, client testimonials, early access waitlist form).
- `runtime/templates.py`:
  - `load_starter_template(site_type, page_file)`: Resolves and loads starter layouts from `/templates`.
  - `fill_template_placeholders(raw, spec, page)`: Deterministically hydrates brand name, taglines, and section titles into starter markup.
  - `FEW_SHOT_EXAMPLES`: Domain-tailored, few-shot inner `<main>` section blocks demonstrating clean component hierarchy, accessible classes, and realistic domain copy.
- `tests/test_templates.py`: 15 comprehensive unit tests verifying template loading across all site types, multi-page template resolution, placeholder hydration, few-shot validity, and 100% compliance of all templates with `base.css` component classes.

### Changed
- `runtime/agent.py`:
  - Injected domain-specific few-shot examples and hydrated starter template layouts directly into the Structure Specialist prompt.
  - Added deterministic fallback: if a small 4B LLM produces empty or truncated markup, the agent automatically falls back to the hydrated starter template rather than writing an empty file.

---

## [Phase 3: Deterministic Theme System & Component Library] - 2026-11-10
### Added
- `runtime/theme.py`:
  - `generate_root_css(theme: ThemeSpec)`: Deterministic synthesizer for CSS custom properties in `:root` (primary, secondary, accent, surface, border, radius scale, layered box-shadows, and spacing scale).
  - `generate_base_css(theme: ThemeSpec)`: Hand-crafted, responsive component library covering `.container`, `.section`, `.section-header`, `.hero`, `.grid`, `.grid-2`, `.grid-3`, `.grid-4`, `.card`, `.btn`, `.btn-primary`, `.btn-outline`, `.btn-accent`, `.badge`, `.form`, `.testimonial`, `.pricing`, `.gallery`, `.faq`, `.stats`, `.navbar`, and `.site-footer`.
  - Accessible focus states (`:focus-visible`), fluid clamp typography, and responsive mobile breakpoints (`@media (max-width: 768px)`).
  - `get_google_fonts_link(font_heading, font_body)`: Generates Google Fonts preconnect and stylesheet link tags.
  - `ALLOWED_COMPONENT_CLASSES`: Strict contract whitelist of standard design system classes for structure and styling agents.
- `tests/test_theme.py`: 5 comprehensive unit tests verifying `:root` variable extraction, component class coverage, brace balance, Google Fonts parsing, and QA color/class compliance.
- `runtime/qa.py` extensions:
  - `audit_theme_colors()`: Flags hardcoded hex colors outside `:root` to enforce variable reuse.
  - `audit_html_classes()`: Validates that all classes used in HTML markup adhere to the design system component whitelist.
  - Verification of `base.css` presence, `:root` definitions, and balanced braces.

### Changed
- `runtime/render.py`: Automatically links both `<link rel="stylesheet" href="base.css">` and `<link rel="stylesheet" href="styles.css">` alongside dynamic Google Fonts links in `<head>`.
- `runtime/roles.py`:
  - Updated `ROLE_STRUCTURE` system prompt to mandate the use of ONLY the standard component classes.
  - Updated `ROLE_STYLE` system prompt to extend `base.css` without redefining `:root` or hard-coding colors.
- `runtime/agent.py`:
  - `task-00-plan` automatically generates and commits `base.css` to the sandbox and blackboard before layout begins.
  - `task-02-styling` provides full multi-page HTML context and `base.css` design system guidelines to the Style Specialist.

---

## [Phase 2: Multi-Page Output & Deterministic Navigation] - 2026-11-10
### Added
- `runtime/render.py`: Deterministic Jinja2 page assembly engine:
  - Generates `<head>`, Google Fonts links, responsive viewport, `<nav class="navbar">` with active navigation pill highlighting, `<main id="main-content">`, and `<footer class="site-footer">` directly in Python.
  - LLM is strictly constrained from writing navbar or footer markup; it only produces inner `<main>` section content.
  - Implemented `extract_clean_main_content()` to reliably strip accidental `<!DOCTYPE html>`, `<html>`, `<head>`, or `<body>` wrappers generated by 4B models.
- `tests/test_render.py`: Unit tests verifying Jinja2 template page assembly, relative link resolution, active nav highlighting, and outer tag stripping.
- `runtime/qa.py`: Added `audit_links()` and multi-page validation in `run_qa_audit()`:
  - Verifies existence of all pages declared in `spec.json`.
  - Audits every `<a href>` to ensure it maps to an existing file in the sandbox or a valid in-page anchor `#id`.
  - Catches dead links, empty `#` placeholders, and missing pages with critical severity defects.
  - Aggregates DOM targets across all pages for JavaScript selector audits.
- Multi-page device frame preview in React frontend (`ui/src/components/PreviewPane.jsx` & `ui/src/App.css`):
  - Page tabs bar above/below browser chrome displaying tabs for each generated `.html` page (`index.html`, `menu.html`, `about.html`, etc.).
  - Iframe navigation interceptor: catches clicks on relative `<a href="*.html">` inside the iframe and seamlessly updates the active tab and preview address bar.

### Changed
- `runtime/agent.py`:
  - `task-00-plan` dynamically seeds structure tasks for every page declared in `spec.pages` (`task-01-structure`, `task-01-structure-<id>`).
  - Re-chains downstream styling (`task-02-styling`), script (`task-03-script`), and QA (`task-04-qa`) tasks to depend on all generated pages.
  - When Structure Specialist writes any `.html` file, it automatically wraps the content using `render_full_page(spec, page, file_content)`.
- `tests/test_baseline.py`: Added `test_phase2_multi_page_navigation_passes` proving multi-page navigation passes QA with 0 broken links.

---

## [Phase 1: Spec Contract (Fixes Requirements)] - 2026-11-10
### Added
- `runtime/spec.py`: Canonical Pydantic v2 data models for `SiteSpec`, `PageSpec`, `SectionSpec`, `ThemeSpec`, `RequirementItem`, and `FooterLink`.
- Deterministic fallback synthesizer `generate_default_spec(prompt)` and robust validator/healer `parse_or_repair_spec(raw, prompt)`.
- Automatic detection of site types (`portfolio`, `restaurant`, `saas`, `store`, `blog`, `landing`, `other`), color modes (dark vs. light), and page topologies.
- `task-00-plan`: Coordinator agent task running as the root dependency before all downstream asset generation tasks.
- Shared `spec.json` artifact written into the sandbox workspace (`.sandbox/<run_id>/spec.json`) and recorded on the SQLite blackboard.
- Injection of `SHARED SITE SPECIFICATION CONTRACT` into every agent's prompt during `step()`, guaranteeing all agents adhere to the exact same brand, pages, navigation, and theme definitions.
- `tests/test_spec.py`: 5 comprehensive unit tests verifying spec validation, site type detection, multi-page bakery defaults, SaaS theme defaults, and fallback healing.

### Changed
- `runtime/roles.py`: Updated `ROLE_COORDINATOR` definition and system prompt to lead architecture planning and enforce `spec.json` contract.
- `runtime/agent.py`: Updated `seed_initial_tasks` to seed `task-00-plan` with priority 10 and chain downstream dependencies (`task-01-structure`, `task-02-styling`, `task-03-script`, `task-04-qa`).

---

## [Phase 0: Audit & Baseline] - 2026-11-10
### Added
- Full codebase audit across frontend, backend, blackboard, agent execution loop, sandboxing, and QA mechanisms.
- `tests/test_baseline.py`: Baseline benchmark capturing empirical metrics on multi-page generation, dead links, spec presence, and legacy QA behavior.
- Fast pytest configuration in `pytest.ini` ignoring standalone interactive scripts.

