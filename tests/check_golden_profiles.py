import ast
import csv
import json
import operator
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = PROJECT_ROOT / "tests" / "golden"
SAFEGUARDS_FILE = PROJECT_ROOT / "data" / "safeguards.csv"

WEIGHTS = {
    "autonomy_level": 0.15,
    "data_level": 0.15,
    "financial_authority": 0.15,
    "oversight_mode": 0.20,
    "affected_population": 0.15,
    "failure_severity": 0.20,
}

DATA_LEVELS = {
    "none": 0,
    "internal": 1,
    "basic_personal": 2,
    "sensitive_personal": 3,
    "special_category": 4,
}

OPERATORS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
}


def is_unknown(value):
    """Return True for missing, None, or blank-string values."""
    return value is None or (isinstance(value, str) and not value.strip())


def to_known_number(value):
    """Convert a known value to a number; preserve unknowns as None."""
    if is_unknown(value) or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate_condition(condition, profile):
    """Evaluate the limited trigger syntax used by safeguards.csv."""
    condition = condition.strip()

    if " AND " in condition:
        return all(
            evaluate_condition(part, profile) for part in condition.split(" AND ")
        )

    if " contains " in condition:
        field, value = condition.split(" contains ", 1)
        actual = profile.get(field.strip(), "")
        if is_unknown(actual):
            return False
        return ast.literal_eval(value.strip()) in str(actual)

    tree = ast.parse(condition, mode="eval").body
    if not isinstance(tree, ast.Compare) or len(tree.ops) != 1:
        raise ValueError(f"Unsupported condition: {condition}")
    if not isinstance(tree.left, ast.Name):
        raise ValueError(f"Unsupported field: {condition}")

    actual = profile.get(tree.left.id, "")
    expected_node = tree.comparators[0]

    if not isinstance(expected_node, ast.Constant):
        raise ValueError(f"Unsupported value: {condition}")

    expected = expected_node.value

    # Unknown values cannot satisfy comparisons.
    if is_unknown(actual):
        return False

    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            actual = float(actual)
        except (TypeError, ValueError):
            return False

    operation = OPERATORS.get(type(tree.ops[0]))
    if operation is None:
        raise ValueError(f"Unsupported operator: {condition}")

    try:
        return operation(actual, expected)
    except (TypeError, ValueError):
        return False


def get_data_level(profile):
    """Return the highest known data-sensitivity level, or None."""
    raw = profile.get("data_categories")

    if is_unknown(raw):
        return None

    categories = [item.strip() for item in str(raw).split(";")]
    levels = [DATA_LEVELS.get(item) for item in categories]

    if any(level is None for level in levels):
        return None

    return max(levels)


def calculate_risk(profile):
    """Calculate the risk tier and red lines without hiding unknowns."""
    values = {
        "autonomy_level": to_known_number(profile.get("autonomy_level")),
        "data_level": get_data_level(profile),
        "financial_authority": to_known_number(profile.get("financial_authority")),
        "oversight_mode": to_known_number(profile.get("oversight_mode")),
        "affected_population": to_known_number(profile.get("affected_population")),
        "failure_severity": to_known_number(profile.get("failure_severity")),
    }

    financial = values["financial_authority"]
    oversight = values["oversight_mode"]
    affected = values["affected_population"]
    failure = values["failure_severity"]
    autonomy = values["autonomy_level"]
    data_level = values["data_level"]

    red_lines = []

    # Critical rule 1: high financial authority and weak oversight.
    if (
        financial is not None
        and oversight is not None
        and financial >= 3
        and oversight >= 3
    ):
        red_lines.append("critical_financial_authority_weak_oversight")

    # Critical rule 2: high-impact harm to affected populations.
    if (
        affected is not None
        and failure is not None
        and oversight is not None
        and affected == 4
        and failure >= 3
        and oversight >= 2
    ):
        red_lines.append("critical_vulnerable_population_harm")

    # Critical rule 3: special-category data and high autonomy.
    if (
        data_level is not None
        and autonomy is not None
        and data_level == 4
        and autonomy >= 3
    ):
        red_lines.append("critical_sensitive_data_high_autonomy")

    # Automatic High rules, as currently documented in the methodology.
    auto_high = (financial is not None and oversight == 2 and financial >= 3) or (
        affected is not None
        and failure is not None
        and oversight is not None
        and affected >= 3
        and failure >= 3
        and oversight >= 2
    )

    # Do not calculate a weighted score if any risk input is unknown.
    if any(value is None for value in values.values()):
        return None, None, red_lines

    score = 100 * sum(WEIGHTS[field] * values[field] / 4 for field in WEIGHTS)

    if score >= 75:
        tier = "Critical"
    elif score >= 50:
        tier = "High"
    elif score >= 25:
        tier = "Moderate"
    else:
        tier = "Low"

    if red_lines:
        tier = "Critical"
    elif auto_high:
        tier = max_tier(tier, "High")

    # A missing accountable owner prevents a Low tier.
    if not profile.get("owner_name"):
        tier = max_tier(tier, "Moderate")

    return score, tier, red_lines


def max_tier(first, second):
    """Return the more severe of two risk tiers."""
    order = ["Low", "Moderate", "High", "Critical"]
    return order[max(order.index(first), order.index(second))]


def main():
    with SAFEGUARDS_FILE.open(newline="", encoding="utf-8") as file:
        safeguards = list(csv.DictReader(file))

    profiles = sorted(GOLDEN_DIR.glob("profile_*.json"))
    if not profiles:
        raise SystemExit(f"No profile_*.json files found in {GOLDEN_DIR}")

    errors = 0

    for profile_path in profiles:
        try:
            with profile_path.open(encoding="utf-8") as file:
                profile = json.load(file)
        except (json.JSONDecodeError, OSError) as error:
            print(f"ERROR: {profile_path.name}: {error}")
            errors += 1
            continue

        triggered = []

        for safeguard in safeguards:
            try:
                if evaluate_condition(safeguard["trigger_condition"], profile):
                    triggered.append(safeguard["id"])
            except (
                SyntaxError,
                ValueError,
                KeyError,
                TypeError,
            ) as error:
                print(
                    f"ERROR: {profile_path.name}: "
                    f"{safeguard.get('id', 'unknown safeguard')}: "
                    f"{error}"
                )
                errors += 1

        expected_safeguards = profile.get("expected_required_safeguards", [])
        expected_red_lines = profile.get("expected_red_lines", [])
        score, tier, red_lines = calculate_risk(profile)

        print(f"\n{profile_path.name}: {profile.get('agent_name', 'Unnamed')}")

        if tier is None:
            print("Risk tier: NOT CALCULATED (unknown risk input)")
            print("Known red lines:", ", ".join(red_lines) or "(none)")

            if profile.get("expected_tier") is not None:
                print("FAIL: profile expects a tier, but inputs are unknown")
                errors += 1

            if set(red_lines) != set(expected_red_lines):
                print("FAIL: red-line mismatch")
                errors += 1
            else:
                print("PASS: red lines match")
        else:
            print(f"Risk score: {score:.2f}")
            print(f"Calculated tier: {tier}")
            print(f"Expected tier:   {profile.get('expected_tier')}")

            if tier != profile.get("expected_tier"):
                print("FAIL: risk tier mismatch")
                errors += 1
            else:
                print("PASS: risk tier matches")

            print(
                "Calculated red lines:",
                ", ".join(red_lines) or "(none)",
            )
            print(
                "Expected red lines:  ",
                ", ".join(expected_red_lines) or "(none)",
            )

            if set(red_lines) != set(expected_red_lines):
                print("FAIL: red-line mismatch")
                errors += 1
            else:
                print("PASS: red lines match")

        print(
            "Triggered safeguards:",
            ", ".join(triggered) or "(none)",
        )
        print(
            "Expected safeguards: ",
            ", ".join(expected_safeguards) or "(none)",
        )

        if set(triggered) != set(expected_safeguards):
            print("FAIL: safeguard mismatch")
            errors += 1
        else:
            print("PASS: safeguards match")

    if errors:
        raise SystemExit(f"\nFinished with {errors} error(s).")

    print("\nAll golden profiles passed.")


if __name__ == "__main__":
    main()
