"""FastAPI endpoints for AgentGuard."""

import asyncio
import io
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import delete, text

from agentguard_core.database import SessionLocal
from agentguard_core.db_models import (
    Agent,
    AgentResultRecord,
    Assessment,
    FindingRecord,
)
from agentguard_core.ingestion import IngestionError, ingest_inventory
from agentguard_core.models import AgentProfile, ReadinessProfile
from agentguard_core.scoring import (
    FAILURE_SCENARIOS,
    RISK_WEIGHTS,
    SAFEGUARDS,
    get_data_level,
    score_agent,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run periodic cleanup of expired assessments."""

    async def cleanup_loop():
        while True:
            try:
                deleted_count = await asyncio.to_thread(cleanup_expired_assessments)
                if deleted_count:
                    print(
                        f"AgentGuard cleanup: deleted "
                        f"{deleted_count} expired assessment(s)."
                    )
            except Exception:
                import logging

                logging.exception("Expired assessment cleanup failed.")

            await asyncio.sleep(15 * 60)

    task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="AgentGuard API", lifespan=lifespan)


@app.get("/guided-assessment")
def guided_assessment_page() -> Response:
    """Display the guided assessment questionnaire."""
    from pathlib import Path

    html_path = Path(__file__).with_name("guided_assessment.html")
    html = html_path.read_text(encoding="utf-8")
    return Response(content=html, media_type="text/html")


@app.get("/upload")
def upload_page() -> Response:
    """Display the inventory upload interface."""
    from pathlib import Path

    html_path = Path(__file__).with_name("upload.html")
    html = html_path.read_text(encoding="utf-8")
    return Response(content=html, media_type="text/html")


@app.get("/dashboard")
def dashboard_page() -> Response:
    """Display the assessment results dashboard."""
    from pathlib import Path

    html_path = Path(__file__).with_name("dashboard.html")
    html = html_path.read_text(encoding="utf-8")
    return Response(content=html, media_type="text/html")


def cleanup_expired_assessments() -> int:
    """Delete expired assessments and their related records."""
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        expired_ids = [
            assessment_id
            for (assessment_id,) in session.query(Assessment.id)
            .filter(Assessment.expires_at <= now)
            .all()
        ]

        if not expired_ids:
            return 0

        agent_ids = [
            agent_id
            for (agent_id,) in session.query(Agent.id)
            .filter(Agent.assessment_id.in_(expired_ids))
            .all()
        ]

        result_ids = []
        if agent_ids:
            result_ids = [
                result_id
                for (result_id,) in session.query(AgentResultRecord.id)
                .filter(AgentResultRecord.agent_id.in_(agent_ids))
                .all()
            ]

        if result_ids:
            session.execute(
                delete(FindingRecord).where(
                    FindingRecord.agent_result_id.in_(result_ids)
                )
            )

        if agent_ids:
            session.execute(
                delete(AgentResultRecord).where(
                    AgentResultRecord.agent_id.in_(agent_ids)
                )
            )
            session.execute(delete(Agent).where(Agent.assessment_id.in_(expired_ids)))

        session.execute(delete(Assessment).where(Assessment.id.in_(expired_ids)))
        session.commit()

        return len(expired_ids)


class GuidedAssessmentRequest(BaseModel):
    """Accept one agent and its optional readiness assessment."""

    model_config = ConfigDict(extra="forbid")

    profile: AgentProfile
    readiness: ReadinessProfile | None = None


def get_active_assessment(session, token: str) -> Assessment:
    """Find an assessment by token and reject missing or expired records."""
    assessment = session.query(Assessment).filter(Assessment.token == token).first()

    if assessment is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment not found.",
        )

    expires_at = assessment.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=410,
            detail="This assessment has expired.",
        )

    return assessment


@app.api_route("/healthz", methods=["GET", "HEAD"])
def health_check() -> dict[str, str]:
    """Check that the API and database are available."""
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return {"status": "unhealthy"}


@app.get("/template")
def get_template() -> Response:
    """Return a blank CSV template for agent assessments."""
    csv_template = (
        "agent_name,purpose,owner_name,owner_role,vendor_or_model,"
        "deployment_status,autonomy_level,data_categories,"
        "financial_authority,oversight_mode,affected_population,"
        "failure_severity,max_transaction_usd,reversibility,"
        "tools_and_integrations,volume_per_week\n"
    )

    return Response(
        content=csv_template,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="agentguard_template.csv"'
        },
    )


@app.post("/assessments/upload")
async def upload_assessment(file: UploadFile = File(...)) -> dict:
    """Validate and score an uploaded CSV or XLSX inventory."""
    filename = file.filename or ""

    try:
        file_bytes = await file.read()
        inventory = ingest_inventory(file_bytes, filename)
    except IngestionError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(error),
                "errors": [],
            },
        ) from error
    finally:
        await file.close()

    readiness_by_row = {
        item["row"]: ReadinessProfile(**item["profile"])
        for item in inventory["readiness_profiles"]
    }

    scored_agents = []
    for item in inventory["agents"]:
        profile = AgentProfile(**item["profile"])
        readiness = readiness_by_row.get(item["row"])
        result = score_agent(profile, readiness)

        scored_agents.append(
            {
                "row": item["row"],
                "profile": profile,
                "result": result,
            }
        )

    token = secrets.token_hex(16)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=24)

    try:
        with SessionLocal.begin() as session:
            assessment = Assessment(
                token=token,
                status="completed",
                created_at=now,
                expires_at=expires_at,
            )
            session.add(assessment)
            session.flush()

            for item in scored_agents:
                profile = item["profile"]
                result = item["result"]

                agent = Agent(
                    assessment_id=assessment.id,
                    agent_name=profile.agent_name,
                    profile=profile.model_dump(mode="json"),
                )
                session.add(agent)
                session.flush()

                result_data = result.model_dump(mode="json")
                result_record = AgentResultRecord(
                    agent_id=agent.id,
                    risk_score=result.risk_score,
                    tier=result.tier,
                    readiness_score=result.readiness_score,
                    result_data=result_data,
                )
                session.add(result_record)
                session.flush()

                for red_line in result.red_lines:
                    session.add(
                        FindingRecord(
                            agent_result_id=result_record.id,
                            rule="red_line",
                            text=red_line,
                            evidence={"agent_name": profile.agent_name},
                        )
                    )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="The assessment could not be saved.",
        ) from error

    return {
        "token": token,
        "status": "completed",
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "total_rows": inventory["total_rows"],
        "valid_agents": inventory["valid_agents"],
        "scored_agents": len(scored_agents),
        "errors": inventory["errors"],
        "results": [
            {
                "row": item["row"],
                **item["result"].model_dump(mode="json"),
            }
            for item in scored_agents
        ],
    }


@app.get("/assessments/{token}")
def get_assessment(token: str) -> dict:
    """Retrieve a saved assessment and its results by token."""
    with SessionLocal() as session:
        assessment = get_active_assessment(session, token)

        agents = session.query(Agent).filter(Agent.assessment_id == assessment.id).all()

        agent_results = []

        for agent in agents:
            result_record = (
                session.query(AgentResultRecord)
                .filter(AgentResultRecord.agent_id == agent.id)
                .first()
            )

            agent_results.append(
                {
                    "agent_name": agent.agent_name,
                    "profile": agent.profile,
                    "result": (
                        result_record.result_data if result_record is not None else None
                    ),
                }
            )

        return {
            "token": assessment.token,
            "status": assessment.status,
            "created_at": assessment.created_at.isoformat(),
            "expires_at": assessment.expires_at.isoformat(),
            "agents": agent_results,
        }


@app.get("/assessments/{token}/dashboard-data")
def get_dashboard_data(token: str) -> dict:
    """Return assessment results enriched for the results dashboard."""
    with SessionLocal() as session:
        assessment = get_active_assessment(session, token)
        agents = session.query(Agent).filter(Agent.assessment_id == assessment.id).all()
        output = []

        for agent in agents:
            record = (
                session.query(AgentResultRecord)
                .filter(AgentResultRecord.agent_id == agent.id)
                .first()
            )
            profile = AgentProfile(**agent.profile)
            result = record.result_data if record is not None else {}
            data_level = get_data_level(profile.data_categories)
            dimensions = {
                "Autonomy": ("autonomy_level", profile.autonomy_level),
                "Data sensitivity": ("data_sensitivity", data_level),
                "Financial authority": (
                    "financial_authority",
                    profile.financial_authority,
                ),
                "Human oversight": ("human_oversight", profile.oversight_mode),
                "Affected population": (
                    "affected_population",
                    profile.affected_population,
                ),
                "Failure consequences": (
                    "failure_consequences",
                    profile.failure_severity,
                ),
            }
            dimension_scores = [
                {
                    "name": label,
                    "value": value,
                    "weighted_points": round(RISK_WEIGHTS[key] * value / 4 * 100, 2)
                    if value is not None
                    else None,
                }
                for label, (key, value) in dimensions.items()
            ]
            required = result.get("required_safeguards", [])
            safeguard_by_id = {item["id"]: item for item in SAFEGUARDS}
            safeguards = []
            for entry in required:
                safeguard_id = entry.split(":", 1)[0].strip()
                source = safeguard_by_id.get(safeguard_id)
                if source:
                    safeguards.append(
                        {
                            "id": safeguard_id,
                            "text": source["safeguard_text"],
                            "priority": source["priority"].lower(),
                            "effort": source["effort"],
                        }
                    )
            profile_terms = set()
            if profile.data_categories:
                profile_terms.add("privacy and data security")
            if profile.autonomy_level is not None and profile.autonomy_level >= 3:
                profile_terms.add("unauthorized actions")
            if profile.failure_severity is not None and profile.failure_severity >= 3:
                profile_terms.update({"human safety", "accuracy and human oversight"})
            if (
                profile.financial_authority is not None
                and profile.financial_authority >= 2
            ):
                profile_terms.add("financial fraud and misinformation")
            scenario = next(
                (
                    item
                    for item in FAILURE_SCENARIOS
                    if any(
                        term in item["risk_dimension"].lower() for term in profile_terms
                    )
                ),
                None,
            )
            output.append(
                {
                    "agent_name": agent.agent_name,
                    "profile": agent.profile,
                    "result": result,
                    "dimension_scores": dimension_scores,
                    "safeguards": safeguards,
                    "failure_scenario": scenario,
                }
            )

        return {
            "token": assessment.token,
            "status": assessment.status,
            "created_at": assessment.created_at.isoformat(),
            "expires_at": assessment.expires_at.isoformat(),
            "agents": output,
        }


@app.post("/assessments/guided")
def guided_assessment(request: GuidedAssessmentRequest) -> dict:
    """Score and save one agent submitted through the guided workflow."""
    profile = request.profile
    result = score_agent(profile, request.readiness)

    token = secrets.token_hex(16)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=24)

    try:
        with SessionLocal.begin() as session:
            assessment = Assessment(
                token=token,
                status="completed",
                created_at=now,
                expires_at=expires_at,
            )
            session.add(assessment)
            session.flush()

            agent = Agent(
                assessment_id=assessment.id,
                agent_name=profile.agent_name,
                profile=profile.model_dump(mode="json"),
            )
            session.add(agent)
            session.flush()

            result_data = result.model_dump(mode="json")
            result_record = AgentResultRecord(
                agent_id=agent.id,
                risk_score=result.risk_score,
                tier=result.tier,
                readiness_score=result.readiness_score,
                result_data=result_data,
            )
            session.add(result_record)
            session.flush()

            for red_line in result.red_lines:
                session.add(
                    FindingRecord(
                        agent_result_id=result_record.id,
                        rule="red_line",
                        text=red_line,
                        evidence={"agent_name": profile.agent_name},
                    )
                )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="The guided assessment could not be saved.",
        ) from error

    return {
        "token": token,
        "status": "completed",
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "scored_agents": 1,
        "results": [result_data],
    }


@app.get("/assessments/{token}/report.pdf")
def download_assessment_report(token: str) -> Response:
    """Generate and download a PDF assessment report."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    _, height = letter

    with SessionLocal() as session:
        assessment = get_active_assessment(session, token)

        agents = session.query(Agent).filter(Agent.assessment_id == assessment.id).all()

        y = height - 50
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(50, y, "AgentGuard Assessment Report")
        y -= 30

        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, y, f"Assessment token: {token}")
        y -= 18
        pdf.drawString(
            50,
            y,
            f"Created: {assessment.created_at.isoformat()}",
        )
        y -= 30

        for agent in agents:
            result_record = (
                session.query(AgentResultRecord)
                .filter(AgentResultRecord.agent_id == agent.id)
                .first()
            )

            if y < 100:
                pdf.showPage()
                y = height - 50

            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawString(50, y, f"Agent: {agent.agent_name[:70]}")
            y -= 20

            if result_record is None:
                pdf.setFont("Helvetica", 10)
                pdf.drawString(60, y, "No scoring result is available.")
                y -= 18
                continue

            pdf.setFont("Helvetica", 10)
            pdf.drawString(
                60,
                y,
                f"Risk score: {result_record.risk_score} | Tier: {result_record.tier}",
            )
            y -= 18

            if result_record.readiness_score is not None:
                pdf.drawString(
                    60,
                    y,
                    f"Readiness score: {result_record.readiness_score}",
                )
                y -= 18

            result_data = result_record.result_data or {}

            for heading, key in (
                ("Required safeguards", "required_safeguards"),
                ("Red lines", "red_lines"),
            ):
                items = result_data.get(key, [])

                if y < 75:
                    pdf.showPage()
                    y = height - 50

                pdf.setFont("Helvetica-Bold", 10)
                pdf.drawString(60, y, f"{heading}:")
                y -= 15

                pdf.setFont("Helvetica", 9)

                if not items:
                    pdf.drawString(70, y, "None recorded")
                    y -= 13
                    continue

                for item in items:
                    if y < 60:
                        pdf.showPage()
                        y = height - 50
                        pdf.setFont("Helvetica", 9)

                    line = f"- {str(item)}"
                    pdf.drawString(70, y, line[:110])
                    y -= 13

            y -= 15

    pdf.save()
    buffer.seek(0)

    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="agentguard_report_{token}.pdf"'
            )
        },
    )
