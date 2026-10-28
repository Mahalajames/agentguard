"""Tests for the grounded governance narrative adapter."""

import json

from agentguard_core.llm_adapter import (
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    generate_fallback_narrative,
    generate_narrative,
    validate_narrative,
)
from agentguard_core.models import AgentProfile, PortfolioResult
from agentguard_core.scoring import score_agent


def make_portfolio() -> dict:
    """Return a portfolio containing one valid finding."""
    return {
        "total_agents": 1,
        "summary": {},
        "results": [
            {
                "agent_name": "Test Agent",
                "findings": [
                    {
                        "id": "F-001",
                        "rule": "test_rule",
                        "text": "Limited oversight was identified.",
                    }
                ],
            }
        ],
    }


def make_narrative(sentence: str) -> dict:
    """Return a narrative with one executive-summary sentence."""
    return {
        "executive_summary": [sentence],
        "agent_explanations": [],
        "plan_30_60_90": [],
    }


class FakeTextBlock:
    """Represent a text block returned by the provider."""

    type = "text"

    def __init__(self, text: str):
        self.text = text


class FakeResponse:
    """Represent a provider response."""

    def __init__(self, narrative: dict):
        self.content = [FakeTextBlock(json.dumps(narrative))]


class FakeMessages:
    """Record calls and return configured provider responses."""

    def __init__(self, responses: list[dict | Exception]):
        self.responses = responses
        self.call_args: list[dict] = []

    def create(self, **kwargs):
        self.call_args.append(kwargs)
        response = self.responses.pop(0)

        if isinstance(response, Exception):
            raise response

        return FakeResponse(response)


class FakeClient:
    """Provide a mock client without making network requests."""

    def __init__(self, responses: list[dict | Exception]):
        self.messages = FakeMessages(responses)


def test_valid_citation_is_retained() -> None:
    """Retain a sentence citing an existing finding ID."""
    result, stats = validate_narrative(
        json.dumps(make_portfolio()),
        json.dumps(make_narrative("Limited oversight was identified. [F-001]")),
    )

    assert len(result.executive_summary) == 1
    assert stats.generated_sentences == 1
    assert stats.retained_sentences == 1
    assert stats.dropped_sentences == 0
    assert stats.grounded_sentence_rate == 1.0
    assert stats.drop_rate == 0.0


def test_invalid_and_missing_citations_are_dropped() -> None:
    """Drop sentences with invented or missing finding IDs."""
    narrative = make_narrative("Supported statement. [F-001]")
    narrative["executive_summary"].extend(
        ["Invented finding. [F-999]", "Uncited statement."]
    )

    result, stats = validate_narrative(
        json.dumps(make_portfolio()),
        json.dumps(narrative),
    )

    assert result.executive_summary == ["Supported statement. [F-001]"]
    assert stats.generated_sentences == 3
    assert stats.retained_sentences == 1
    assert stats.dropped_sentences == 2


def test_empty_narrative_has_no_drops() -> None:
    """Handle an empty model response without dividing by zero."""
    result, stats = validate_narrative(
        json.dumps(make_portfolio()),
        json.dumps(make_narrative_empty()),
    )

    assert result.executive_summary == []
    assert stats.generated_sentences == 0
    assert stats.retained_sentences == 0
    assert stats.dropped_sentences == 0
    assert stats.grounded_sentence_rate == 1.0
    assert stats.drop_rate == 0.0


def make_narrative_empty() -> dict:
    """Return a narrative with all three sections empty."""
    return {
        "executive_summary": [],
        "agent_explanations": [],
        "plan_30_60_90": [],
    }


def test_all_sentences_dropped_when_portfolio_has_no_findings() -> None:
    """Never retain sentences when the portfolio has no valid finding IDs."""
    portfolio = make_portfolio()
    portfolio["results"][0]["findings"] = []

    result, stats = validate_narrative(
        json.dumps(portfolio),
        json.dumps(make_narrative("Unsupported statement. [F-001]")),
    )

    assert result.executive_summary == []
    assert stats.retained_sentences == 0
    assert stats.dropped_sentences == 1


def test_validator_accepts_finding_generated_by_scoring() -> None:
    """Accept citations for findings produced by the scoring engine."""
    profile = AgentProfile(
        agent_name="Test Agent",
        owner_name="Project Manager",
        autonomy_level=3,
        data_categories="special_category",
        financial_authority=0,
        oversight_mode=0,
        affected_population=0,
        failure_severity=0,
    )
    result = score_agent(profile)
    portfolio = {
        "total_agents": 1,
        "summary": {},
        "results": [result.model_dump(mode="json")],
    }
    finding_id = result.findings[0].id

    grounded, stats = validate_narrative(
        json.dumps(portfolio),
        json.dumps(
            make_narrative(
                "Sensitive data and high autonomy triggered a "
                f"red-line rule. [{finding_id}]"
            )
        ),
    )

    assert len(grounded.executive_summary) == 1
    assert stats.retained_sentences == 1
    assert stats.dropped_sentences == 0


def test_generate_narrative_uses_client_and_logs_metrics(caplog) -> None:
    """Verify provider settings, citation validation, and metric logging."""
    caplog.set_level("INFO")
    client = FakeClient([make_narrative("Limited oversight was identified. [F-001]")])

    narrative, stats = generate_narrative(
        json.dumps(make_portfolio()),
        assessment_id="assessment-test-123",
        client=client,
    )

    assert narrative.executive_summary == ["Limited oversight was identified. [F-001]"]
    assert stats.retained_sentences == 1
    assert stats.dropped_sentences == 0
    assert client.messages.call_args[0]["model"] == DEFAULT_MODEL
    assert client.messages.call_args[0]["temperature"] == DEFAULT_TEMPERATURE
    assert "assessment_id=assessment-test-123" in caplog.text


def test_fallback_generates_all_three_sections() -> None:
    """Generate all narrative sections using portfolio findings."""
    portfolio = PortfolioResult.model_validate(make_portfolio())
    narrative = generate_fallback_narrative(portfolio.model_dump_json())

    assert narrative.executive_summary
    assert narrative.agent_explanations
    assert narrative.plan_30_60_90

    for section in (
        narrative.executive_summary,
        narrative.agent_explanations,
        narrative.plan_30_60_90,
    ):
        for sentence in section:
            assert any(
                f"[{finding.id}]" in sentence
                for result in portfolio.results
                for finding in result.findings
            )


def test_fallback_handles_empty_portfolio() -> None:
    """Return empty sections when the portfolio contains no agents."""
    portfolio = PortfolioResult(
        results=[],
        total_agents=0,
        summary={},
    )
    narrative = generate_fallback_narrative(portfolio.model_dump_json())

    assert narrative.executive_summary == []
    assert narrative.agent_explanations == []
    assert narrative.plan_30_60_90 == []


def test_generate_narrative_retries_after_grounding_failure() -> None:
    """Retry once when the first response contains an uncited sentence."""
    client = FakeClient(
        [
            make_narrative("Unsupported statement."),
            make_narrative("Limited oversight was identified. [F-001]"),
        ]
    )

    narrative, stats = generate_narrative(
        json.dumps(make_portfolio()),
        client=client,
    )

    assert len(client.messages.call_args) == 2
    assert narrative.executive_summary == ["Limited oversight was identified. [F-001]"]
    assert stats.dropped_sentences == 0


def test_generate_narrative_uses_fallback_after_two_grounding_failures() -> None:
    """Use the deterministic fallback if both model responses fail validation."""
    portfolio_json = json.dumps(make_portfolio())
    client = FakeClient(
        [
            make_narrative("Unsupported first response."),
            make_narrative("Unsupported second response."),
        ]
    )

    narrative, _stats = generate_narrative(
        portfolio_json,
        client=client,
    )
    fallback = generate_fallback_narrative(portfolio_json)

    assert len(client.messages.call_args) == 2
    assert narrative == fallback


def test_generate_narrative_uses_fallback_when_provider_fails() -> None:
    """Use the deterministic fallback when the provider raises an error."""
    portfolio_json = json.dumps(make_portfolio())
    client = FakeClient([RuntimeError("Provider unavailable")])

    narrative, _stats = generate_narrative(
        portfolio_json,
        client=client,
    )

    assert narrative == generate_fallback_narrative(portfolio_json)


def test_generate_narrative_uses_fallback_when_token_ceiling_is_exceeded(
    monkeypatch,
) -> None:
    """Use the deterministic fallback when the configured ceiling is too low."""
    portfolio_json = json.dumps(make_portfolio())
    monkeypatch.setenv("AGENTGUARD_ASSESSMENT_TOKEN_CEILING", "0")
    client = FakeClient([])

    narrative, _stats = generate_narrative(
        portfolio_json,
        client=client,
    )

    assert client.messages.call_args == []
    assert narrative == generate_fallback_narrative(portfolio_json)


def test_generate_narrative_uses_fallback_without_api_key(monkeypatch) -> None:
    """Use the deterministic fallback when no provider key is configured."""
    portfolio_json = json.dumps(make_portfolio())
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    narrative, _stats = generate_narrative(portfolio_json)

    assert narrative == generate_fallback_narrative(portfolio_json)
