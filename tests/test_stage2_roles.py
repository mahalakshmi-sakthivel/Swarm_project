"""
Unit tests for Stage 2 Swarm Roles and Role Routing.
"""

import sys
sys.path.insert(0, ".")

import pytest
from runtime.roles import (
    ALL_ROLES,
    ROLE_STRUCTURE,
    ROLE_STYLE,
    ROLE_SCRIPT,
    ROLE_QA,
    ROLE_COORDINATOR,
    ROLE_CONTENT,
    get_role_by_hint
)


def test_all_six_roles_registered():
    assert len(ALL_ROLES) == 6
    assert set(ALL_ROLES.keys()) == {"structure", "style", "script", "qa", "integration", "content"}


def test_role_attributes_and_system_prompts():
    for name, role in ALL_ROLES.items():
        assert role.name == name
        assert role.default_agent_id.startswith("agent-")
        assert len(role.system_prompt) > 50
        assert len(role.target_files) >= 1


def test_role_resolution_by_hint_and_aliases():
    assert get_role_by_hint("structure") == ROLE_STRUCTURE
    assert get_role_by_hint("Frontend Structure Specialist") == ROLE_STRUCTURE
    assert get_role_by_hint("style") == ROLE_STYLE
    assert get_role_by_hint("CSS Specialist") == ROLE_STYLE
    assert get_role_by_hint("script") == ROLE_SCRIPT
    assert get_role_by_hint("Interactivity Specialist") == ROLE_SCRIPT
    assert get_role_by_hint("qa") == ROLE_QA
    assert get_role_by_hint("Critic") == ROLE_QA
    assert get_role_by_hint("integration") == ROLE_COORDINATOR
    assert get_role_by_hint("Coordinator") == ROLE_COORDINATOR
    assert get_role_by_hint("content") == ROLE_CONTENT
    assert get_role_by_hint("Copywriter") == ROLE_CONTENT


def test_sensitive_signals():
    assert "need_styling" in ROLE_STYLE.sensitive_signals
    assert "need_script" in ROLE_SCRIPT.sensitive_signals
    assert "need_qa" in ROLE_QA.sensitive_signals
    assert "need_integration" in ROLE_COORDINATOR.sensitive_signals

