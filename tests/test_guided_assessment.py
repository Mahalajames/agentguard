from fastapi.testclient import TestClient

from agentguard_core.api import app


def test_guided_assessment_page_contains_questionnaire():
    with TestClient(app) as client:
        response = client.get("/guided-assessment")

    assert response.status_code == 200

    page = response.text
    assert "When this agent decides something should happen, what happens next?" in page
    assert (
        "What is the most sensitive information this agent can see or change?" in page
    )
    assert "I don't know" in page
    assert "Add another agent" in page
    assert "Review answers" in page
