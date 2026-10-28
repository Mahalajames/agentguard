"""Provider-agnostic LLM adapter for grounded AgentGuard narratives."""

import logging
import os
import re
from pathlib import Path
from typing import Any

import anthropic
from pydantic import BaseModel, ConfigDict, Field

from agentguard_core.models import PortfolioResult

CITATION_PATTERN = re.compile(r"\[([A-Za-z0-9_-]+)\]")
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "governance_v1.txt"

DEFAULT_MODEL = "claude-haiku-5-5"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_OUTPUT_TOKENS = 2000

logger = logging.getLogger(__name__)


class GovernanceNarrative(BaseModel):
    """Structured narrative returned by the LLM or deterministic fallback."""

    model_config = ConfigDict(extra="forbid")

    executive_summary: list[str] = Field(default_factory=list)
    agent_explanations: list[str] = Field(default_factory=list)
    plan_30_60_90: list[str] = Field(default_factory=list)


class GroundingStats(BaseModel):
    """Metrics describing the citation validation of generated sentences."""

    model_config = ConfigDict(extra="forbid")

    generated_sentences: int = Field(ge=0)
    retained_sentences: int = Field(ge=0)
    dropped_sentences: int = Field(ge=0)
    grounded_sentence_rate: float = Field(ge=0, le=1)
    drop_rate: float = Field(ge=0, le=1)


def estimate_input_tokens(text: str) -> int:
    """Estimate input tokens conservatively from text length."""
    return (len(text) + 2) // 3


def check_token_ceiling(estimated_tokens: int) -> bool:
    """Return whether estimated usage fits the configured assessment ceiling."""
    raw_ceiling = os.getenv("AGENTGUARD_ASSESSMENT_TOKEN_CEILING", "12000")

    try:
        ceiling = int(raw_ceiling)
    except ValueError as exc:
        raise ValueError(
            "AGENTGUARD_ASSESSMENT_TOKEN_CEILING must be an integer."
        ) from exc

    if estimated_tokens < 0 or ceiling < 0:
        raise ValueError("Token estimates and ceiling cannot be negative.")

    return estimated_tokens <= ceiling


def validate_narrative(
    portfolio_json: str,
    narrative_json: str,
) -> tuple[GovernanceNarrative, GroundingStats]:
    """Drop every sentence that lacks valid finding-ID citations."""
    portfolio = PortfolioResult.model_validate_json(portfolio_json)
    narrative = GovernanceNarrative.model_validate_json(narrative_json)

    valid_ids = {
        finding.id for result in portfolio.results for finding in result.findings
    }

    section_names = (
        "executive_summary",
        "agent_explanations",
        "plan_30_60_90",
    )

    generated = 0
    retained = 0
    dropped = 0
    grounded_sections: dict[str, list[str]] = {}

    for section_name in section_names:
        grounded_sentences: list[str] = []

        for sentence in getattr(narrative, section_name):
            generated += 1
            cited_ids = CITATION_PATTERN.findall(sentence)

            if cited_ids and all(finding_id in valid_ids for finding_id in cited_ids):
                grounded_sentences.append(sentence)
                retained += 1
            else:
                dropped += 1

        grounded_sections[section_name] = grounded_sentences

    grounded_narrative = GovernanceNarrative.model_validate(grounded_sections)

    stats = GroundingStats(
        generated_sentences=generated,
        retained_sentences=retained,
        dropped_sentences=dropped,
        grounded_sentence_rate=retained / generated if generated else 1.0,
        drop_rate=dropped / generated if generated else 0.0,
    )

    return grounded_narrative, stats


def _empty_grounding_stats() -> GroundingStats:
    """Return zero-sentence metrics for an empty narrative."""
    return GroundingStats(
        generated_sentences=0,
        retained_sentences=0,
        dropped_sentences=0,
        grounded_sentence_rate=1.0,
        drop_rate=0.0,
    )


def _log_grounding_stats(
    stats: GroundingStats,
    assessment_id: str | None,
) -> None:
    """Log grounding metrics for an assessment."""
    logger.info(
        "LLM grounding metrics: assessment_id=%s "
        "grounded_sentence_rate=%.4f drop_rate=%.4f "
        "generated_sentences=%d retained_sentences=%d "
        "dropped_sentences=%d",
        assessment_id or "unassigned",
        stats.grounded_sentence_rate,
        stats.drop_rate,
        stats.generated_sentences,
        stats.retained_sentences,
        stats.dropped_sentences,
    )


def _use_fallback(
    portfolio_json: str,
    assessment_id: str | None,
) -> tuple[GovernanceNarrative, GroundingStats]:
    """Create a deterministic narrative and calculate its grounding metrics."""
    narrative = generate_fallback_narrative(portfolio_json)
    _, stats = validate_narrative(
        portfolio_json,
        narrative.model_dump_json(),
    )

    _log_grounding_stats(stats, assessment_id)

    logger.info(
        "Using deterministic narrative fallback: assessment_id=%s",
        assessment_id or "unassigned",
    )

    return narrative, stats


def generate_narrative(
    portfolio_json: str,
    *,
    assessment_id: str | None = None,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
) -> tuple[GovernanceNarrative, GroundingStats]:
    """Generate a grounded narrative with retry and deterministic fallback."""
    portfolio = PortfolioResult.model_validate_json(portfolio_json)

    if not 0.0 <= temperature <= 0.2:
        raise ValueError("Temperature must be between 0.0 and 0.2.")

    valid_finding_ids = {
        finding.id for result in portfolio.results for finding in result.findings
    }

    if not valid_finding_ids:
        return GovernanceNarrative(), _empty_grounding_stats()

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    portfolio_text = portfolio.model_dump_json()
    user_content = (
        f"Create the governance narrative for this assessment JSON:\n{portfolio_text}"
    )

    estimated_total_tokens = (
        estimate_input_tokens(prompt + user_content) + DEFAULT_MAX_OUTPUT_TOKENS
    )

    try:
        within_ceiling = check_token_ceiling(estimated_total_tokens)
    except ValueError:
        logger.exception("Invalid assessment token ceiling configuration")
        return _use_fallback(portfolio_json, assessment_id)

    if not within_ceiling:
        logger.warning(
            "Assessment token ceiling exceeded: assessment_id=%s",
            assessment_id or "unassigned",
        )
        return _use_fallback(portfolio_json, assessment_id)

    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            logger.warning(
                "Anthropic API key is missing: assessment_id=%s",
                assessment_id or "unassigned",
            )
            return _use_fallback(portfolio_json, assessment_id)

        try:
            client = anthropic.Anthropic()
        except Exception:
            logger.exception("Could not initialize the LLM provider")
            return _use_fallback(portfolio_json, assessment_id)

    for attempt in range(2):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
                temperature=temperature,
                system=prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_content,
                    }
                ],
            )

            response_text = "".join(
                block.text
                for block in response.content
                if getattr(block, "type", None) == "text"
            )

            narrative, stats = validate_narrative(
                portfolio_text,
                response_text,
            )

        except Exception:
            logger.exception(
                "LLM generation or validation failed: assessment_id=%s attempt=%d",
                assessment_id or "unassigned",
                attempt + 1,
            )
            return _use_fallback(portfolio_json, assessment_id)

        _log_grounding_stats(stats, assessment_id)

        if stats.dropped_sentences == 0:
            return narrative, stats

        if attempt == 0:
            logger.warning(
                "Grounding validation failed; retrying once: assessment_id=%s",
                assessment_id or "unassigned",
            )

    logger.warning(
        "Grounding validation failed twice; using fallback: assessment_id=%s",
        assessment_id or "unassigned",
    )
    return _use_fallback(portfolio_json, assessment_id)


def generate_fallback_narrative(portfolio_json: str) -> GovernanceNarrative:
    """Build all three narrative sections from recorded findings only."""
    portfolio = PortfolioResult.model_validate_json(portfolio_json)

    executive_summary: list[str] = []
    agent_explanations: list[str] = []
    plan_30_60_90: list[str] = []

    for result in portfolio.results:
        if not result.findings:
            continue

        citations = " ".join(f"[{finding.id}]" for finding in result.findings)

        executive_summary.append(
            f"{result.agent_name} has a risk tier of {result.tier} "
            f"and a readiness score of {result.readiness_score}; "
            f"review its recorded findings {citations}."
        )

        for finding in result.findings:
            agent_explanations.append(
                f"{result.agent_name}: {finding.text} [{finding.id}]"
            )

        plan_30_60_90.append(
            f"Review the recorded findings for {result.agent_name} "
            f"and address applicable items through existing required "
            f"safeguards {citations}."
        )

    return GovernanceNarrative(
        executive_summary=executive_summary,
        agent_explanations=agent_explanations,
        plan_30_60_90=plan_30_60_90,
    )
