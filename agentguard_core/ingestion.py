"""Read and validate AgentGuard inventory files."""

import csv
import io
import re
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from pydantic import BaseModel, ValidationError

from agentguard_core.models import AgentProfile, ReadinessProfile

# A file must contain this column to be accepted.
REQUIRED_COLUMNS = {"agent_name"}

# Common alternative column names.
HEADER_ALIASES = {
    "agent": "agent_name",
    "name": "agent_name",
    "owner": "owner_name",
    "vendor": "vendor_or_model",
    "model": "vendor_or_model",
    "autonomy": "autonomy_level",
    "oversight": "oversight_mode",
    "affected_users": "affected_population",
    "failure_consequences": "failure_severity",
}

AGENT_FIELDS = set(AgentProfile.model_fields)
READINESS_FIELDS = set(ReadinessProfile.model_fields)
ALL_FIELDS = AGENT_FIELDS | READINESS_FIELDS


class IngestionError(ValueError):
    """Raised when an inventory file cannot be read or accepted."""


def normalize_header(value: Any) -> str:
    """Standardize a column name and apply known aliases."""
    if value is None:
        return ""

    header = str(value).strip().lower()
    header = re.sub(r"[^a-z0-9]+", "_", header).strip("_")

    return HEADER_ALIASES.get(header, header)


def _clean_value(value: Any) -> Any:
    """Convert blank cells and whitespace-only strings into None."""
    if isinstance(value, str):
        value = value.strip()
        return value if value else None

    return value


def _read_rows(
    file_bytes: bytes, filename: str
) -> tuple[list[str], list[tuple[int, dict[str, Any]]], list[str]]:
    """Read CSV or XLSX data in memory without saving the uploaded file."""
    extension = Path(filename).suffix.lower()

    if extension == ".csv":
        try:
            text = file_bytes.decode("utf-8-sig")
            reader = csv.reader(io.StringIO(text))
            raw_headers = next(reader, [])
            file_rows = list(reader)
        except (UnicodeDecodeError, csv.Error) as exc:
            raise IngestionError(
                "The CSV file could not be read. Check its format and "
                "make sure it uses UTF-8 text."
            ) from exc

    elif extension == ".xlsx":
        try:
            workbook = load_workbook(
                io.BytesIO(file_bytes),
                read_only=True,
                data_only=True,
            )

            try:
                worksheet = workbook.active
                all_rows = worksheet.iter_rows(values_only=True)
                raw_headers = list(next(all_rows, ()))
                file_rows = [list(row) for row in all_rows]
            finally:
                workbook.close()

        except Exception as exc:
            raise IngestionError(
                "The Excel file could not be read. Check that it is a "
                "valid .xlsx file and try again."
            ) from exc

    else:
        raise IngestionError(
            "Unsupported file type. Please upload a .csv or .xlsx file."
        )

    # Keep original names for helpful error messages.
    original_headers = [
        str(value).strip() if value is not None else "" for value in raw_headers
    ]
    headers = [normalize_header(value) for value in raw_headers]

    rows = []

    for row_number, values in enumerate(file_rows, start=2):
        # Ignore completely empty rows.
        if not any(value is not None and str(value).strip() for value in values):
            continue

        row_data = {
            header: values[index] if index < len(values) else None
            for index, header in enumerate(headers)
            if header
        }

        rows.append((row_number, row_data))

    return headers, rows, original_headers


def _validate_profile(
    model: type[BaseModel],
    values: dict[str, Any],
    row_number: int,
    errors: list[dict[str, Any]],
) -> BaseModel | None:
    """Validate a profile and record row-level errors."""
    try:
        return model(**values)

    except ValidationError as exc:
        for issue in exc.errors():
            location = issue.get("loc", ())
            column = str(location[0]) if location else "row"
            message = issue.get("msg", "Invalid value")

            errors.append(
                {
                    "row": row_number,
                    "column": column,
                    "message": (f"{message}. Please check the value in '{column}'."),
                }
            )

        return None


def ingest_inventory(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Read an inventory file and validate its agent and readiness profiles."""
    headers, rows, original_headers = _read_rows(file_bytes, filename)
    errors: list[dict[str, Any]] = []

    # Reject the file only when a required column is missing.
    missing_columns = sorted(REQUIRED_COLUMNS - set(headers))

    if missing_columns:
        missing_text = ", ".join(missing_columns)
        raise IngestionError(
            f"Missing required column(s): {missing_text}. "
            "Please add the required column and upload the file again."
        )

    # Reject duplicate headers after normalization.
    duplicate_headers = sorted(
        {header for header in headers if header and headers.count(header) > 1}
    )

    if duplicate_headers:
        duplicate_text = ", ".join(duplicate_headers)
        raise IngestionError(
            f"Duplicate columns found: {duplicate_text}. "
            "Please rename or remove the duplicate columns."
        )

    agents = []
    readiness_profiles = []

    for row_number, row in rows:
        agent_values = {
            key: _clean_value(value)
            for key, value in row.items()
            if key in AGENT_FIELDS
        }

        readiness_values = {
            key: _clean_value(value)
            for key, value in row.items()
            if key in READINESS_FIELDS
        }

        agent = _validate_profile(
            AgentProfile,
            agent_values,
            row_number,
            errors,
        )

        if agent is not None:
            agents.append(
                {
                    "row": row_number,
                    "profile": agent.model_dump(),
                }
            )

        readiness = _validate_profile(
            ReadinessProfile,
            readiness_values,
            row_number,
            errors,
        )

        if readiness is not None:
            readiness_profiles.append(
                {
                    "row": row_number,
                    "profile": readiness.model_dump(),
                }
            )

        # Report unknown columns while allowing valid data to continue.
        for index, header in enumerate(headers):
            if header and header not in ALL_FIELDS:
                original_header = original_headers[index]

                errors.append(
                    {
                        "row": row_number,
                        "column": header,
                        "message": (
                            f"Unrecognized column '{original_header}'. "
                            "This column was ignored."
                        ),
                    }
                )

    return {
        "agents": agents,
        "readiness_profiles": readiness_profiles,
        "total_rows": len(rows),
        "valid_agents": len(agents),
        "errors": errors,
    }
