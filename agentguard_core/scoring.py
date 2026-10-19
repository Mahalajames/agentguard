"""Risk scoring calculations for AgentGuard."""

import csv
import re
from pathlib import Path

from agentguard_core.models import AgentProfile, AgentResult, ReadinessProfile

RISK_WEIGHTS = {
    "autonomy_level": 0.15,
    "data_sensitivity": 0.15,
    "financial_authority": 0.15,
    "human_oversight": 0.20,
    "affected_population": 0.15,
    "failure_consequences": 0.20,
}

DATA_LEVELS = {
    "none": 0,
    "internal": 1,
    "basic_personal": 2,
    "sensitive_personal": 3,
    "special_category": 4,
}


def get_data_level(raw: str | int | None) -> int | None:
    """Return the highest known data-sensitivity level, or None."""
    if raw is None or raw == "":
        return None

    if isinstance(raw, int):
        return raw if 0 <= raw <= 4 else None

    categories = [item.strip() for item in raw.split(";")]

    if not categories or any(item not in DATA_LEVELS for item in categories):
        return None

    return max(DATA_LEVELS[item] for item in categories)


def calculate_risk_score(profile: AgentProfile) -> float | None:
    """Calculate the weighted risk score from 0 to 100.

    Returns None if any required risk dimension is unknown.
    """
    values = {
        "autonomy_level": profile.autonomy_level,
        "data_sensitivity": get_data_level(profile.data_categories),
        "financial_authority": profile.financial_authority,
        "human_oversight": profile.oversight_mode,
        "affected_population": profile.affected_population,
        "failure_consequences": profile.failure_severity,
    }

    if any(value is None for value in values.values()):
        return None

    weighted_total = sum(
        RISK_WEIGHTS[dimension] * value for dimension, value in values.items()
    )

    return round(weighted_total / 4 * 100, 2)


def assign_tier(risk_score: float | None) -> str | None:
    """Assign an initial risk tier based on the weighted score."""
    if risk_score is None:
        return None
    if not 0 <= risk_score <= 100:
        raise ValueError("Risk score must be between 0 and 100.")
    if risk_score < 25:
        return "Low"
    if risk_score < 50:
        return "Moderate"
    if risk_score < 75:
        return "High"
    return "Critical"


def apply_red_lines(profile: AgentProfile) -> list[str]:
    """Return the IDs of all red-line rules triggered by an agent."""
    triggered = []

    autonomy = profile.autonomy_level
    data_level = get_data_level(profile.data_categories)
    financial = profile.financial_authority
    oversight = profile.oversight_mode
    affected = profile.affected_population
    failure = profile.failure_severity

    # Automatic Critical rules
    if financial is not None and oversight is not None:
        if financial >= 3 and oversight >= 3:
            triggered.append("RL-CRIT-01")

    if affected is not None and failure is not None and oversight is not None:
        if affected == 4 and failure >= 3 and oversight >= 2:
            triggered.append("RL-CRIT-02")

    if data_level is not None and autonomy is not None:
        if data_level == 4 and autonomy >= 3:
            triggered.append("RL-CRIT-03")

    # Automatic High rules
    if financial is not None and oversight is not None:
        if financial >= 3 and oversight == 2:
            triggered.append("RL-HIGH-01")

    if affected is not None and failure is not None and oversight is not None:
        if affected >= 3 and failure >= 3 and oversight >= 2:
            triggered.append("RL-HIGH-02")

    return triggered


def finalize_tier(
    risk_score: float | None,
    red_lines: list[str],
    owner_name: str | None,
) -> str | None:
    """Apply red-line and missing-owner rules to the initial tier."""
    tier = assign_tier(risk_score)

    if tier is None:
        return None

    # Critical red lines always force Critical.
    if any(rule.startswith("RL-CRIT-") for rule in red_lines):
        return "Critical"

    # High red lines require at least High.
    tier_order = ["Low", "Moderate", "High", "Critical"]
    if any(rule.startswith("RL-HIGH-") for rule in red_lines):
        if tier_order.index(tier) < tier_order.index("High"):
            tier = "High"

    # An agent without a named owner cannot be Low.
    if not owner_name or not owner_name.strip():
        if tier == "Low":
            tier = "Moderate"

    return tier


def matrix_position(profile: AgentProfile) -> dict[str, int] | None:
    """Calculate the likelihood and severity positions for the risk matrix."""
    data_level = get_data_level(profile.data_categories)

    values = [
        profile.autonomy_level,
        profile.oversight_mode,
        profile.failure_severity,
        profile.affected_population,
        profile.financial_authority,
        data_level,
    ]

    if any(value is None for value in values):
        return None

    likelihood = round((profile.autonomy_level + profile.oversight_mode) / 2)

    severity = round(
        (
            profile.failure_severity
            + profile.affected_population
            + max(profile.financial_authority, data_level)
        )
        / 3
    )

    return {
        "likelihood": likelihood,
        "severity": severity,
    }


def score_readiness(profile: ReadinessProfile) -> float:
    """Calculate readiness, scoring unknown controls as zero."""
    values = [
        getattr(profile, field_name) for field_name in ReadinessProfile.model_fields
    ]

    if not values:
        return 0.0

    total = sum(value if value is not None else 0 for value in values)
    return round(total / (len(values) * 2) * 100, 2)


def score_agent(
    profile: AgentProfile,
    readiness: ReadinessProfile | None = None,
) -> AgentResult:
    """Calculate risk, readiness, safeguards, and matrix position."""
    risk_score = calculate_risk_score(profile)
    red_lines = apply_red_lines(profile)
    safeguards = required_safeguards(profile, readiness)
    tier = finalize_tier(risk_score, red_lines, profile.owner_name)
    review_plan = human_review_plan(profile, tier)

    return AgentResult(
        agent_name=profile.agent_name,
        risk_score=risk_score,
        tier=tier,
        matrix_position=matrix_position(profile),
        red_lines=red_lines,
        readiness_score=(score_readiness(readiness) if readiness is not None else None),
        required_safeguards=safeguards,
        human_review_plan=review_plan,
    )


def load_safeguards() -> list[dict[str, str]]:
    """Load and validate safeguard rules from the project CSV file."""
    csv_path = Path(__file__).resolve().parent.parent / "data" / "safeguards.csv"

    required_columns = {
        "id",
        "trigger_condition",
        "safeguard_text",
        "nist_ai_rmf_function",
        "nist_ai_rmf_subcategory",
        "priority",
        "effort",
    }

    try:
        with csv_path.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise ValueError("Safeguards CSV is missing its header row.")

            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError("Safeguards CSV contains duplicate column names.")

            missing_columns = required_columns - set(reader.fieldnames)
            if missing_columns:
                raise ValueError(
                    f"Safeguards CSV is missing columns: {sorted(missing_columns)}"
                )

            safeguards = []
            seen_ids = set()

            for row_number, row in enumerate(reader, start=2):
                if None in row:
                    raise ValueError(
                        f"Safeguards CSV row {row_number} has extra columns."
                    )

                if any(value is None for value in row.values()):
                    raise ValueError(
                        f"Safeguards CSV row {row_number} has missing values."
                    )

                for column in required_columns:
                    if not row[column].strip():
                        raise ValueError(
                            f"Safeguards CSV row {row_number} "
                            f"has an empty required field: {column}."
                        )

                safeguard_id = row["id"].strip()

                if safeguard_id in seen_ids:
                    raise ValueError(
                        f"Duplicate safeguard ID {safeguard_id!r} on row {row_number}."
                    )

                seen_ids.add(safeguard_id)
                safeguards.append(row)

            if not safeguards:
                raise ValueError("Safeguards CSV contains no safeguard records.")

            return safeguards

    except csv.Error as error:
        raise ValueError(f"Could not parse safeguards CSV: {error}") from error


# Load the safeguard library once when this module is imported.
SAFEGUARDS = load_safeguards()


def load_failure_scenarios() -> list[dict[str, str]]:
    """Load and validate failure scenarios from the project CSV file."""
    csv_path = Path(__file__).resolve().parent.parent / "data" / "failure_scenarios.csv"

    required_columns = {
        "incident_id",
        "incident_name",
        "incident_date",
        "source_name",
        "source_url",
        "incident_summary",
        "agent_type",
        "risk_dimension",
        "risk_level",
        "consequence",
        "lesson",
    }

    try:
        with csv_path.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise ValueError("Failure scenarios CSV is missing its header row.")

            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError(
                    "Failure scenarios CSV contains duplicate column names."
                )

            missing_columns = required_columns - set(reader.fieldnames)
            if missing_columns:
                raise ValueError(
                    "Failure scenarios CSV is missing columns: "
                    f"{sorted(missing_columns)}"
                )

            scenarios = []
            seen_ids = set()

            for row_number, row in enumerate(reader, start=2):
                if None in row:
                    raise ValueError(
                        f"Failure scenarios CSV row {row_number} has extra columns."
                    )

                if any(value is None for value in row.values()):
                    raise ValueError(
                        f"Failure scenarios CSV row {row_number} has missing values."
                    )

                for column in required_columns:
                    if not row[column].strip():
                        raise ValueError(
                            f"Failure scenarios CSV row {row_number} "
                            f"has an empty required field: {column}."
                        )

                scenario_id = row["incident_id"].strip()

                if scenario_id in seen_ids:
                    raise ValueError(
                        f"Duplicate incident ID {scenario_id!r} on row {row_number}."
                    )

                seen_ids.add(scenario_id)
                scenarios.append(row)

            if not scenarios:
                raise ValueError("Failure scenarios CSV contains no incident records.")

            return scenarios

    except csv.Error as error:
        raise ValueError(f"Could not parse failure scenarios CSV: {error}") from error


# Load failure scenarios once when this module is imported.
FAILURE_SCENARIOS = load_failure_scenarios()


def condition_matches(
    condition: str,
    values: dict[str, object],
) -> bool:
    """Safely evaluate a supported safeguard trigger condition."""
    parts = re.split(r"\s+AND\s+", condition, flags=re.IGNORECASE)

    for part in parts:
        match = re.fullmatch(
            r"\s*([a-z_]+)\s*(>=|==|!=|contains)\s*(.*?)\s*",
            part,
            flags=re.IGNORECASE,
        )

        if not match:
            return False

        field, operator, expected = match.groups()
        actual = values.get(field)

        # Unknown values can trigger a safeguard when a requirement
        # cannot be verified through a "not equal" condition.
        operator = operator.lower()
        if actual is None:
            if operator == "!=":
                continue
            return False
        expected = expected.strip()

        # Remove surrounding quotes from text values.
        if (
            len(expected) >= 2
            and expected[0] == expected[-1]
            and expected[0] in ("'", '"')
        ):
            expected = expected[1:-1]

        if operator == "contains":
            if expected not in str(actual):
                return False

        elif operator in (">=", "==", "!="):
            try:
                expected_number = float(expected)
                numeric_comparison = True
            except ValueError:
                numeric_comparison = False

            if numeric_comparison:
                try:
                    actual_number = float(actual)
                except (TypeError, ValueError):
                    return False

                if operator == ">=" and not actual_number >= expected_number:
                    return False
                if operator == "==" and not actual_number == expected_number:
                    return False
                if operator == "!=" and not actual_number != expected_number:
                    return False

            else:
                actual_text = str(actual)

                if operator == ">=":
                    return False
                if operator == "==" and actual_text != expected:
                    return False
                if operator == "!=" and actual_text == expected:
                    return False

    return True


def required_safeguards(
    profile: AgentProfile,
    readiness: ReadinessProfile | None = None,
) -> list[str]:
    """Return the IDs and descriptions of safeguards triggered by an agent."""
    values: dict[str, object] = profile.model_dump()

    if readiness is not None:
        values.update(readiness.model_dump())

    selected = []

    for safeguard in SAFEGUARDS:
        if condition_matches(safeguard["trigger_condition"], values):
            selected.append(f"{safeguard['id']}: {safeguard['safeguard_text']}")

    return selected


def human_review_plan(
    profile: AgentProfile,
    tier: str | None,
) -> list[str]:
    """Recommend human oversight based on risk and agent characteristics."""
    plan = []

    if tier in ("High", "Critical"):
        plan.append("Require documented human approval before consequential actions.")
        plan.append("Assign a named reviewer to regularly inspect agent activity.")

    if tier == "Critical":
        plan.append(
            "Do not deploy until critical risks have been reviewed and "
            "appropriate safeguards are verified."
        )

    if profile.oversight_mode is not None and profile.oversight_mode >= 3:
        plan.append("Strengthen human oversight because current oversight is weak.")

    if (
        profile.data_categories is not None
        and "sensitive_personal" in str(profile.data_categories)
    ) or (
        profile.data_categories is not None
        and "special_category" in str(profile.data_categories)
    ):
        plan.append("Require human review of sensitive-data access and handling.")

    return list(dict.fromkeys(plan))
