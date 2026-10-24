from fastapi.testclient import TestClient

from agentguard_core.api import app


def test_dashboard_page_contains_results_interface():
    with TestClient(app) as client:
        response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Results dashboard" in response.text
    assert "Risk matrix" in response.text
    assert "Readiness overview" in response.text
    assert "Agent assessments" in response.text
    assert "Human-review plan" in response.text
    assert "Safeguards checklist" in response.text
    assert "priority-filter" in response.text
