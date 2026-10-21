import csv
import io

import pytest
from openpyxl import Workbook

from agentguard_core.ingestion import IngestionError, ingest_inventory

HEADERS = [
    "agent_name",
    "purpose",
    "owner_name",
    "autonomy_level",
    "data_categories",
    "financial_authority",
    "oversight_mode",
    "affected_population",
    "failure_severity",
    "r_owner",
    "r_data_inventory",
]


def make_csv(headers=HEADERS, rows=None):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)

    for row in rows or []:
        writer.writerow(row)

    return output.getvalue().encode("utf-8")


def make_xlsx(headers=HEADERS, rows=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)

    for row in rows or []:
        sheet.append(row)

    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def valid_row():
    return [
        "FAQ Assistant",
        "Drafts internal answers for human review.",
        "Jordan Smith",
        1,
        "internal",
        0,
        1,
        1,
        1,
        2,
        1,
    ]


def test_ingests_valid_csv():
    result = ingest_inventory(make_csv(rows=[valid_row()]), "inventory.csv")

    assert result["total_rows"] == 1
    assert result["valid_agents"] == 1
    assert result["agents"][0]["profile"]["agent_name"] == "FAQ Assistant"
    assert result["errors"] == []


def test_ingests_valid_xlsx():
    result = ingest_inventory(make_xlsx(rows=[valid_row()]), "inventory.xlsx")

    assert result["total_rows"] == 1
    assert result["valid_agents"] == 1
    assert result["agents"][0]["profile"]["agent_name"] == "FAQ Assistant"


def test_normalizes_headers_and_owner_alias():
    headers = [
        "Agent Name",
        "Purpose",
        "Owner",
        "Autonomy Level",
        "Data Categories",
        "Financial Authority",
        "Oversight Mode",
        "Affected Population",
        "Failure Severity",
        "R Owner",
        "R Data Inventory",
    ]

    result = ingest_inventory(make_csv(headers, [valid_row()]), "inventory.csv")

    profile = result["agents"][0]["profile"]
    assert profile["agent_name"] == "FAQ Assistant"
    assert profile["owner_name"] == "Jordan Smith"
    assert result["errors"] == []


def test_invalid_row_generates_errors_but_valid_row_survives():
    bad_row = valid_row()
    bad_row[3] = 9  # Autonomy must be between 0 and 4.

    result = ingest_inventory(make_csv(rows=[bad_row, valid_row()]), "inventory.csv")

    assert result["total_rows"] == 2
    assert result["valid_agents"] == 1
    assert len(result["errors"]) >= 1
    assert result["errors"][0]["row"] == 2
    assert result["errors"][0]["column"] == "autonomy_level"


def test_missing_required_column_rejects_file():
    headers = ["purpose", "owner_name"]

    with pytest.raises(IngestionError, match="agent_name"):
        ingest_inventory(make_csv(headers=headers), "inventory.csv")


def test_unsupported_file_type_is_rejected():
    with pytest.raises(IngestionError, match="Unsupported file type"):
        ingest_inventory(b"example", "inventory.txt")


def test_duplicate_headers_are_rejected():
    headers = HEADERS + ["Agent Name"]

    with pytest.raises(IngestionError, match="Duplicate columns"):
        ingest_inventory(make_csv(headers=headers), "inventory.csv")


def test_invalid_readiness_value_generates_error():
    bad_row = valid_row()
    bad_row[9] = 5  # r_owner must be between 0 and 2.

    result = ingest_inventory(make_csv(rows=[bad_row]), "inventory.csv")

    assert result["valid_agents"] == 1
    assert any(error["column"] == "r_owner" for error in result["errors"])


def test_unknown_column_is_reported_without_rejecting_valid_row():
    headers = HEADERS + ["Extra Notes"]
    row = valid_row() + ["Some additional information"]

    result = ingest_inventory(make_csv(headers, [row]), "inventory.csv")

    assert result["valid_agents"] == 1
    assert any("Extra Notes" in error["message"] for error in result["errors"])
