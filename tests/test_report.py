from pathlib import Path

from agentguard_core.models import PortfolioResult
from agentguard_core.report import (
    check_assessment_token_ceiling,
    get_monthly_spend_cap,
    render_governance_report,
    save_governance_report_pdf,
)


def empty_portfolio_json() -> str:
    portfolio = PortfolioResult.model_validate(
        {"total_agents": 0, "summary": {}, "results": []}
    )
    return portfolio.model_dump_json()


def test_html_report_contains_required_sections() -> None:
    html = render_governance_report(
        empty_portfolio_json(),
        organization_name="Test Organization",
        assessment_id="test-001",
    )

    assert "Test Organization" in html
    assert "test-001" in html
    assert "Executive Summary" in html
    assert "Agent Inventory" in html
    assert "Risk Matrix" in html
    assert "Safeguards Checklist" in html
    assert "Human-Review Plan" in html
    assert "30/60/90-Day Plan" in html
    assert "not legal advice" in html.lower()


def test_pdf_report_is_created(tmp_path: Path) -> None:
    html = render_governance_report(empty_portfolio_json())
    pdf_path = save_governance_report_pdf(html, tmp_path / "report.pdf")

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
    assert pdf_path.read_bytes().startswith(b"%PDF-")


def test_monthly_spend_cap_defaults_to_25_dollars(
    monkeypatch,
) -> None:
    monkeypatch.delenv("AGENTGUARD_MONTHLY_LLM_SPEND_CAP_USD", raising=False)

    assert get_monthly_spend_cap() == 25.0


def test_monthly_spend_cap_reads_environment(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTGUARD_MONTHLY_LLM_SPEND_CAP_USD", "40")

    assert get_monthly_spend_cap() == 40.0


def test_assessment_token_ceiling() -> None:
    assert check_assessment_token_ceiling(100, ceiling=100)
    assert not check_assessment_token_ceiling(101, ceiling=100)


def test_html_report_embeds_generated_risk_matrix() -> None:
    html = render_governance_report(empty_portfolio_json())

    assert 'src="data:image/png;base64,' in html
    assert "Risk matrix image was not provided" not in html


def test_populated_portfolio_renders_agent_and_matrix() -> None:
    portfolio = PortfolioResult.model_validate(
        {
            "total_agents": 1,
            "summary": {"Moderate": 1},
            "results": [
                {
                    "agent_name": "Test Support Agent",
                    "risk_score": 45,
                    "tier": "Moderate",
                    "matrix_position": {"likelihood": 2, "severity": 3},
                    "readiness_score": 60,
                    "findings": [],
                    "required_safeguards": [],
                    "human_review_plan": [],
                }
            ],
        }
    )

    html = render_governance_report(portfolio.model_dump_json())

    assert "Test Support Agent" in html
    assert "data:image/png;base64," in html
    assert "Risk matrix image was not provided" not in html
