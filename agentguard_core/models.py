"""Validated data models for the AgentGuard scoring engine."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = int | None
ReadinessLevel = int | None
RiskTier = Literal["Low", "Moderate", "High", "Critical"]


class AgentProfile(BaseModel):
    """Describe an AI agent and its six risk dimensions."""

    model_config = ConfigDict(extra="forbid")

    agent_name: str = Field(min_length=1)
    purpose: str = ""
    owner_name: str | None = None
    owner_role: str | None = None
    vendor_or_model: str | None = None
    deployment_status: str | None = None

    autonomy_level: RiskLevel = Field(default=None, ge=0, le=4)
    data_categories: str | int | None = None
    financial_authority: RiskLevel = Field(default=None, ge=0, le=4)
    oversight_mode: RiskLevel = Field(default=None, ge=0, le=4)
    affected_population: RiskLevel = Field(default=None, ge=0, le=4)
    failure_severity: RiskLevel = Field(default=None, ge=0, le=4)

    # Additional context that does not directly change the risk score.
    max_transaction_usd: float | None = Field(default=None, ge=0)
    reversibility: str | None = None
    tools_and_integrations: str | None = None
    volume_per_week: int | None = Field(default=None, ge=0)


class ReadinessProfile(BaseModel):
    """Represent the ten organizational readiness controls."""

    model_config = ConfigDict(extra="forbid")

    r_owner: ReadinessLevel = Field(default=None, ge=0, le=2)
    r_data_inventory: ReadinessLevel = Field(default=None, ge=0, le=2)
    r_scope_limits: ReadinessLevel = Field(default=None, ge=0, le=2)
    r_logging: ReadinessLevel = Field(default=None, ge=0, le=2)
    r_kill_switch: ReadinessLevel = Field(default=None, ge=0, le=2)
    r_review_process: ReadinessLevel = Field(default=None, ge=0, le=2)
    r_testing: ReadinessLevel = Field(default=None, ge=0, le=2)
    r_incident_plan: ReadinessLevel = Field(default=None, ge=0, le=2)
    r_vendor_terms: ReadinessLevel = Field(default=None, ge=0, le=2)
    r_transparency: ReadinessLevel = Field(default=None, ge=0, le=2)


class Finding(BaseModel):
    """Explain a rule result in plain language with supporting evidence."""

    model_config = ConfigDict(extra="forbid")

    id: str
    rule: str
    evidence_fields: list[str] = Field(default_factory=list)
    evidence_values: dict[str, Any] = Field(default_factory=dict)
    text: str
    framework_references: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    """Store the assessment results for one agent."""

    model_config = ConfigDict(extra="forbid")

    agent_name: str
    risk_score: float | None = Field(default=None, ge=0, le=100)
    tier: RiskTier | None = None
    matrix_position: dict[str, int] | None = None
    red_lines: list[str] = Field(default_factory=list)
    readiness_score: float | None = Field(default=None, ge=0, le=100)
    required_safeguards: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    human_review_plan: list[str] = Field(default_factory=list)


class PortfolioResult(BaseModel):
    """Collect the assessment results for an inventory of agents."""

    model_config = ConfigDict(extra="forbid")

    results: list[AgentResult] = Field(default_factory=list)
    total_agents: int = Field(default=0, ge=0)
    summary: dict[str, int] = Field(default_factory=dict)
