from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from agentguard_core.api import app
from agentguard_core.ingestion import IngestionError, ingest_inventory


def test_upload_rejects_unsupported_extension():
    with TestClient(app) as client:
        response = client.post(
            "/assessments/upload",
            files={"file": ("inventory.json", b'{"agent_name": "Test"}')},
        )

    assert response.status_code == 415


def test_upload_rejects_files_over_5_mb():
    oversized_file = b"x" * (5 * 1024 * 1024 + 1)

    with TestClient(app) as client:
        response = client.post(
            "/assessments/upload",
            files={"file": ("inventory.csv", oversized_file)},
        )

    assert response.status_code == 413


def test_upload_closes_file_after_processing():
    with (
        patch(
            "agentguard_core.api.ingest_inventory",
            side_effect=IngestionError("test"),
        ),
        TestClient(app) as client,
    ):
        response = client.post(
            "/assessments/upload",
            files={
                "file": (
                    "inventory.csv",
                    b"agent_name,environment\nTest,production\n",
                )
            },
        )

    assert response.status_code == 422


def test_ingestion_does_not_persist_raw_upload(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    file_bytes = b"agent_name,environment\nTest Agent,production\n"

    ingest_inventory(file_bytes, "inventory.csv")

    assert list(tmp_path.iterdir()) == []


def test_upload_rate_limit():
    with TestClient(app, client=("198.51.100.10", 50000)) as client:
        responses = []

        for _ in range(6):
            response = client.post(
                "/assessments/upload",
                files={
                    "file": (
                        "inventory.json",
                        b'{"agent_name": "Test"}',
                    )
                },
            )
            responses.append(response)

    assert all(response.status_code == 415 for response in responses[:5])
    assert responses[5].status_code == 429


def test_report_rate_limit():
    with (
        patch("agentguard_core.api.SessionLocal") as mock_session_local,
        TestClient(app, client=("198.51.100.20", 50000)) as client,
    ):
        mock_session = mock_session_local.return_value.__enter__.return_value

        mock_assessment = type(
            "AssessmentStub",
            (),
            {
                "id": 1,
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(days=1),
            },
        )()

        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_assessment
        )

        mock_session.query.return_value.filter.return_value.all.return_value = []

        responses = []

        for _ in range(11):
            response = client.get("/assessments/nonexistent-token/report.pdf")
            responses.append(response)

    assert all(response.status_code != 429 for response in responses[:10])
    assert responses[10].status_code == 429
