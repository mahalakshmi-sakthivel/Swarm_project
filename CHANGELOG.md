# Changelog

All notable changes to the Swarm Website Builder project will be documented in this file.

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
