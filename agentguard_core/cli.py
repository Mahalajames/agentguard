import csv
import json
from pathlib import Path
from typing import Annotated

import typer

from agentguard_core.models import AgentProfile
from agentguard_core.scoring import score_agent

app = typer.Typer(help="AgentGuard risk and readiness assessment CLI.")


@app.command()
def template() -> None:
    """Print the required inventory CSV columns."""
    columns = [
        "agent_name",
        "purpose",
        "owner_name",
        "autonomy_level",
        "data_categories",
        "financial_authority",
        "oversight_mode",
        "affected_population",
        "failure_severity",
    ]
    writer = csv.writer(__import__("sys").stdout)
    writer.writerow(columns)


@app.command()
def score(
    inventory: Annotated[
        Path,
        typer.Argument(help="Path to the inventory CSV file."),
    ],
    out: Annotated[
        Path,
        typer.Option("--out", help="Path for the JSON results file."),
    ],
) -> None:
    """Score agents listed in an inventory CSV file."""
    with inventory.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise typer.BadParameter("Inventory CSV must include a header row.")

        results = []
        for row_number, row in enumerate(reader, start=2):
            try:
                profile = AgentProfile.model_validate(row)
                results.append(score_agent(profile).model_dump(mode="json"))
            except Exception as error:
                raise typer.BadParameter(
                    f"Invalid inventory data on row {row_number}: {error}"
                ) from error

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    typer.echo(f"Scored {len(results)} agent(s). Results saved to {out}.")


if __name__ == "__main__":
    app()
