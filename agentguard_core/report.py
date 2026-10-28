"""Render AgentGuard governance reports as HTML and PDF."""

import base64
import os
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from agentguard_core.llm_adapter import (
    GovernanceNarrative,
    generate_fallback_narrative,
)
from agentguard_core.models import PortfolioResult
from agentguard_core.risk_matrix import generate_risk_matrix_png

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates"
DEFAULT_MONTHLY_SPEND_CAP_USD = 25.0


def render_governance_report(
    portfolio_json: str,
    *,
    organization_name: str = "Organization not specified",
    assessment_id: str = "unassigned",
    assessment_date: str | None = None,
    narrative: GovernanceNarrative | None = None,
    risk_matrix_image: str | None = None,
) -> str:
    """Render a governance report with an automatically generated risk matrix."""
    portfolio = PortfolioResult.model_validate_json(portfolio_json)

    if narrative is None:
        narrative = generate_fallback_narrative(portfolio_json)

    if risk_matrix_image is None:
        matrix_png = generate_risk_matrix_png(portfolio)
        risk_matrix_image = "data:image/png;base64," + base64.b64encode(
            matrix_png
        ).decode("ascii")

    environment = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = environment.get_template("governance_report.html")

    return template.render(
        organization_name=organization_name,
        assessment_id=assessment_id,
        assessment_date=assessment_date or date.today().isoformat(),
        portfolio=portfolio,
        narrative=narrative,
        risk_matrix_image=risk_matrix_image,
    )


def save_governance_report_pdf(
    html: str,
    output_path: str | Path,
) -> Path:
    """Write rendered report HTML to a PDF file."""
    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    HTML(
        string=html,
        base_url=str(PROJECT_ROOT),
    ).write_pdf(destination)

    return destination


def get_monthly_spend_cap() -> float:
    """Read the configured monthly LLM spend cap in USD."""
    value = os.getenv(
        "AGENTGUARD_MONTHLY_LLM_SPEND_CAP_USD",
        str(DEFAULT_MONTHLY_SPEND_CAP_USD),
    )
    try:
        cap = float(value)
    except ValueError as exc:
        raise ValueError(
            "AGENTGUARD_MONTHLY_LLM_SPEND_CAP_USD must be numeric."
        ) from exc

    if cap < 0:
        raise ValueError("The monthly LLM spend cap cannot be negative.")

    return cap


def check_assessment_token_ceiling(
    estimated_tokens: int,
    *,
    ceiling: int | None = None,
) -> bool:
    """Return whether an assessment fits its configured token ceiling."""
    if estimated_tokens < 0:
        raise ValueError("Estimated tokens cannot be negative.")

    if ceiling is None:
        raw_ceiling = os.getenv("AGENTGUARD_ASSESSMENT_TOKEN_CEILING", "12000")
        try:
            ceiling = int(raw_ceiling)
        except ValueError as exc:
            raise ValueError(
                "AGENTGUARD_ASSESSMENT_TOKEN_CEILING must be an integer."
            ) from exc

    if ceiling < 0:
        raise ValueError("The assessment token ceiling cannot be negative.")

    return estimated_tokens <= ceiling
