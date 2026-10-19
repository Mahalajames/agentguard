import json

from typer.testing import CliRunner

from agentguard_core.cli import app

runner = CliRunner()


def test_template_command_prints_inventory_columns():
    result = runner.invoke(app, ["template"])

    assert result.exit_code == 0
    assert "agent_name" in result.stdout
    assert "autonomy_level" in result.stdout
    assert "failure_severity" in result.stdout


def test_score_command_creates_json_results(tmp_path):
    inventory = tmp_path / "inventory.csv"
    output = tmp_path / "results.json"

    inventory.write_text(
        "agent_name,purpose,owner_name,autonomy_level,data_categories,"
        "financial_authority,oversight_mode,affected_population,"
        "failure_severity\n"
        "Test FAQ Agent,Internal FAQ assistant,Project Manager,"
        "1,internal,0,1,0,1\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["score", str(inventory), "--out", str(output)],
    )

    assert result.exit_code == 0
    assert "Scored 1 agent(s)" in result.stdout
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["risk_score"] is not None
    assert data[0]["tier"] is not None
