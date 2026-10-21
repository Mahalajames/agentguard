"""Load AgentGuard reference data from CSV files into PostgreSQL."""

import csv
import os
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert

from agentguard_core.db_models import FailureScenario, Safeguard

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://agentguard:agentguard_dev_password@localhost:5432/agentguard",
)

DATA_DIR = Path(__file__).parent / "data"


def read_csv(filename: str) -> list[dict[str, str]]:
    """Read a CSV file into dictionaries."""
    with (DATA_DIR / filename).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def seed_table(engine, model, rows: list[dict], date_columns=()) -> int:
    """Insert CSV rows, updating existing rows with matching primary keys."""
    for row in rows:
        for column in date_columns:
            row[column] = date.fromisoformat(row[column])

    if not rows:
        return 0

    with engine.begin() as connection:
        statement = insert(model).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=[column.name for column in model.__table__.primary_key],
            set_={
                column.name: statement.excluded[column.name]
                for column in model.__table__.columns
                if not column.primary_key
            },
        )
        connection.execute(statement)

    return len(rows)


def main() -> None:
    """Load both reference-data CSV files."""
    engine = create_engine(DATABASE_URL)

    safeguards = read_csv("safeguards.csv")
    scenarios = read_csv("failure_scenarios.csv")

    safeguard_count = seed_table(engine, Safeguard, safeguards)
    scenario_count = seed_table(
        engine,
        FailureScenario,
        scenarios,
        date_columns=("incident_date",),
    )

    print(f"Loaded {safeguard_count} safeguards.")
    print(f"Loaded {scenario_count} failure scenarios.")
    engine.dispose()


if __name__ == "__main__":
    main()
