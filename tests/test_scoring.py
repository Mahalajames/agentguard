import pytest

from agentguard_core.models import AgentProfile, ReadinessProfile
from agentguard_core.scoring import (
    apply_red_lines,
    assign_tier,
    calculate_risk_score,
    condition_matches,
    finalize_tier,
    matrix_position,
    required_safeguards,
    score_agent,
    score_readiness,
)


def make_profile(**overrides):
    """Create a valid baseline agent profile for tests."""
    values = {
        "agent_name": "Test Agent",
        "purpose": "Internal FAQ assistant",
        "owner_name": "Project Manager",
        "autonomy_level": 0,
        "data_categories": "internal",
        "financial_authority": 0,
        "oversight_mode": 0,
        "affected_population": 0,
        "failure_severity": 0,
    }
    values.update(overrides)
    return AgentProfile(**values)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0, "Low"),
        (24, "Low"),
        (25, "Moderate"),
        (49, "Moderate"),
        (50, "High"),
        (74, "High"),
        (75, "Critical"),
        (100, "Critical"),
        (None, None),
    ],
)
def test_assign_tier_boundaries(score, expected):
    assert assign_tier(score) == expected


def test_low_risk_profile_score():
    profile = make_profile()
    assert calculate_risk_score(profile) == 3.75


def test_unknown_risk_dimension_returns_none():
    profile = make_profile(autonomy_level=None)
    assert calculate_risk_score(profile) is None


def test_critical_red_line_forces_critical_tier():
    profile = make_profile(
        autonomy_level=3,
        data_categories="special_category",
    )
    red_lines = apply_red_lines(profile)
    assert "RL-CRIT-03" in red_lines
    assert finalize_tier(10, red_lines, profile.owner_name) == "Critical"


def test_missing_owner_cannot_be_low():
    assert finalize_tier(10, [], None) == "Moderate"


def test_matrix_position():
    profile = make_profile(
        autonomy_level=2,
        oversight_mode=2,
        failure_severity=3,
        affected_population=3,
        financial_authority=3,
    )
    assert matrix_position(profile) == {
        "likelihood": 2,
        "severity": 3,
    }


def test_safeguard_trigger_numeric_and_combined():
    assert condition_matches(
        "autonomy_level >= 3",
        {"autonomy_level": 3},
    )
    assert condition_matches(
        "oversight_mode >= 2 AND failure_severity >= 3",
        {"oversight_mode": 2, "failure_severity": 3},
    )


def test_unknown_trigger_value_does_not_match():
    assert not condition_matches(
        "autonomy_level >= 3",
        {"autonomy_level": None},
    )


def test_safeguards_are_returned_for_high_autonomy():
    profile = make_profile(autonomy_level=3)
    safeguards = required_safeguards(profile)
    assert any(item.startswith("SG-002:") for item in safeguards)


def test_readiness_score():
    complete = ReadinessProfile(**{field: 2 for field in ReadinessProfile.model_fields})
    assert score_readiness(complete) == 100.0
    assert score_readiness(ReadinessProfile()) is None


def test_score_agent_returns_safeguards_and_review_plan():
    profile = make_profile(
        autonomy_level=3,
        data_categories="sensitive_personal",
        oversight_mode=3,
        failure_severity=2,
    )
    result = score_agent(profile)
    assert result.risk_score is not None
    assert result.tier == "Moderate"
    assert result.required_safeguards
    assert result.human_review_plan
