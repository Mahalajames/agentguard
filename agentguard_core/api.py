"""FastAPI endpoints for AgentGuard."""

import asyncio
import hashlib
import logging
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import delete, text

from agentguard_core.database import SessionLocal
from agentguard_core.db_models import (
    Agent,
    AgentResultRecord,
    Assessment,
    FindingRecord,
    LoginSession,
    Organization,
    User,
)
from agentguard_core.ingestion import IngestionError, ingest_inventory
from agentguard_core.models import (
    AgentProfile,
    AgentResult,
    PortfolioResult,
    ReadinessProfile,
)
from agentguard_core.report import (
    render_governance_report,
    render_governance_report_pdf_bytes,
)
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


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="AgentGuard API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


SESSION_COOKIE_NAME = "agentguard_session"
SESSION_DURATION = timedelta(days=30)
PASSWORD_HASHER = PasswordHash.recommended()


class SignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=128)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def valid_email(email: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_current_user(session, request: Request) -> User | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    login_session = (
        session.query(LoginSession)
        .filter(
            LoginSession.token_hash == hash_session_token(token),
            LoginSession.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if login_session is None:
        return None

    user = session.query(User).filter(User.id == login_session.user_id).first()
    if user is None or not user.is_active:
        return None

    return user


def create_login_session(session, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)

    session.add(
        LoginSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            created_at=now,
            expires_at=now + SESSION_DURATION,
        )
    )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/",
    )


def ensure_assessment_access(session, assessment: Assessment, request: Request) -> None:
    """Restrict account-owned assessments to their owner."""
    if getattr(assessment, "user_id", None) is None:
        return

    user = get_current_user(session, request)
    if user is None or user.id != assessment.user_id:
        raise HTTPException(status_code=404, detail="Assessment not found.")


@app.post("/auth/signup", status_code=201)
@limiter.limit("5/minute")
def signup(payload: SignupRequest, request: Request, response: Response) -> dict:
    """Create an account and sign the new user in."""
    email = normalize_email(payload.email)

    if not valid_email(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")

    with SessionLocal.begin() as session:
        existing = session.query(User).filter(User.email == email).first()
        if existing is not None:
            raise HTTPException(
                status_code=409, detail="An account with that email already exists."
            )

        user = User(
            email=email,
            password_hash=PASSWORD_HASHER.hash(payload.password),
            is_active=True,
        )
        session.add(user)
        session.flush()
        create_login_session(session, user, response)

        return {"id": user.id, "email": user.email}


@app.post("/auth/login")
@limiter.limit("5/minute")
def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    """Authenticate an existing user and create a browser session."""
    email = normalize_email(payload.email)

    with SessionLocal.begin() as session:
        user = session.query(User).filter(User.email == email).first()

        if (
            user is None
            or not user.is_active
            or not PASSWORD_HASHER.verify(payload.password, user.password_hash)
        ):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        create_login_session(session, user, response)
        return {"id": user.id, "email": user.email}


@app.post("/auth/logout")
def logout(request: Request, response: Response) -> dict:
    """Revoke the current login session."""
    token = request.cookies.get(SESSION_COOKIE_NAME)

    if token:
        with SessionLocal.begin() as session:
            session.query(LoginSession).filter(
                LoginSession.token_hash == hash_session_token(token)
            ).delete(synchronize_session=False)

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
    )
    return {"message": "Signed out."}


@app.get("/auth/me")
def get_account(request: Request) -> dict:
    """Return the currently authenticated account."""
    with SessionLocal() as session:
        user = get_current_user(session, request)
        if user is None:
            raise HTTPException(status_code=401, detail="Please sign in.")
        return {"id": user.id, "email": user.email}


@app.get("/account/assessments")
def get_account_assessments(request: Request) -> dict:
    """List assessments belonging to the signed-in account."""
    with SessionLocal() as session:
        user = get_current_user(session, request)
        if user is None:
            raise HTTPException(status_code=401, detail="Please sign in.")

        assessments = (
            session.query(Assessment)
            .filter(Assessment.user_id == user.id)
            .order_by(Assessment.created_at.desc())
            .all()
        )

        return {
            "assessments": [
                {
                    "token": item.token,
                    "status": item.status,
                    "created_at": item.created_at.isoformat(),
                    "expires_at": item.expires_at.isoformat()
                    if item.expires_at
                    else None,
                }
                for item in assessments
            ]
        }


@app.get("/")
def homepage() -> Response:
    """Display the AgentGuard homepage."""
    html_path = Path(__file__).with_name("homepage.html")
    html = html_path.read_text(encoding="utf-8")
    return Response(content=html, media_type="text/html")


@app.get("/methodology")
def methodology_page() -> Response:
    """Display the public AgentGuard scoring methodology."""
    html_path = Path(__file__).with_name("methodology.html")
    return Response(
        content=html_path.read_text(encoding="utf-8"), media_type="text/html"
    )


@app.get("/login")
def login_page() -> Response:
    html_path = Path(__file__).with_name("login.html")
    return Response(
        content=html_path.read_text(encoding="utf-8"), media_type="text/html"
    )


@app.get("/signup")
def signup_page() -> Response:
    html_path = Path(__file__).with_name("signup.html")
    return Response(
        content=html_path.read_text(encoding="utf-8"), media_type="text/html"
    )


@app.get("/account")
def account_page() -> Response:
    html_path = Path(__file__).with_name("account.html")
    return Response(
        content=html_path.read_text(encoding="utf-8"), media_type="text/html"
    )


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
            .filter(
                Assessment.user_id.is_(None),
                Assessment.expires_at <= now,
            )
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
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at is not None and expires_at <= datetime.now(timezone.utc):
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
@limiter.limit("5/minute")
async def upload_assessment(request: Request, file: UploadFile = File(...)) -> dict:
    """Validate and score an uploaded CSV or XLSX inventory."""
    filename = file.filename or ""
    allowed_extensions = {".csv", ".xlsx"}
    max_upload_bytes = 5 * 1024 * 1024

    try:
        if Path(filename).suffix.lower() not in allowed_extensions:
            raise HTTPException(
                status_code=415,
                detail="Only CSV and XLSX files are supported.",
            )

        file_bytes = await file.read(max_upload_bytes + 1)

        if len(file_bytes) > max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail="Upload exceeds the 5 MB file size limit.",
            )

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
            user = get_current_user(session, request)
            expires_at = None if user else now + timedelta(hours=24)

            assessment = Assessment(
                token=token,
                user_id=user.id if user else None,
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
        "expires_at": expires_at.isoformat() if expires_at else None,
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
def get_assessment(token: str, request: Request) -> dict:
    """Retrieve a saved assessment and its results by token."""
    with SessionLocal() as session:
        assessment = get_active_assessment(session, token)
        ensure_assessment_access(session, assessment, request)

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
            "expires_at": assessment.expires_at.isoformat()
            if assessment.expires_at
            else None,
            "agents": agent_results,
        }


@app.get("/assessments/{token}/dashboard-data")
def get_dashboard_data(token: str, request: Request) -> dict:
    """Return assessment results enriched for the results dashboard."""
    with SessionLocal() as session:
        assessment = get_active_assessment(session, token)
        ensure_assessment_access(session, assessment, request)
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

        current_user = get_current_user(session, request)
        is_saved_to_account = (
            current_user is not None
            and assessment.user_id is not None
            and current_user.id == assessment.user_id
        )

        return {
            "token": assessment.token,
            "status": assessment.status,
            "created_at": assessment.created_at.isoformat(),
            "expires_at": assessment.expires_at.isoformat()
            if assessment.expires_at
            else None,
            "is_saved_to_account": is_saved_to_account,
            "agents": output,
        }


@app.post("/assessments/{token}/claim")
def claim_assessment(token: str, request: Request) -> dict:
    """Save a guest assessment permanently to the signed-in account."""
    with SessionLocal.begin() as session:
        user = get_current_user(session, request)
        if user is None:
            raise HTTPException(
                status_code=401, detail="Please sign in to save this assessment."
            )

        # Lock the row so two accounts cannot claim it concurrently.
        assessment = (
            session.query(Assessment)
            .filter(Assessment.token == token)
            .with_for_update()
            .first()
        )

        if assessment is None:
            raise HTTPException(status_code=404, detail="Assessment not found.")

        # Reuse the normal missing/expiration checks before claiming.
        get_active_assessment(session, token)

        if assessment.user_id is not None:
            if assessment.user_id == user.id:
                return {
                    "saved": True,
                    "already_saved": True,
                    "token": assessment.token,
                }
            raise HTTPException(status_code=404, detail="Assessment not found.")

        assessment.user_id = user.id
        assessment.expires_at = None
        session.flush()

        return {
            "saved": True,
            "already_saved": False,
            "token": assessment.token,
        }


@app.post("/assessments/guided")
def guided_assessment(request: GuidedAssessmentRequest, http_request: Request) -> dict:
    """Score and save one agent submitted through the guided workflow."""
    profile = request.profile
    result = score_agent(profile, request.readiness)

    token = secrets.token_hex(16)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=24)

    try:
        with SessionLocal.begin() as session:
            user = get_current_user(session, http_request)
            expires_at = None if user else now + timedelta(hours=24)

            assessment = Assessment(
                token=token,
                user_id=user.id if user else None,
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
        logging.exception("Guided assessment save failed")
        raise HTTPException(
            status_code=500,
            detail="The guided assessment could not be saved.",
        ) from error

    return {
        "token": token,
        "status": "completed",
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "scored_agents": 1,
        "results": [result_data],
    }


@app.get("/assessments/{token}/report.pdf")
@limiter.limit("10/minute")
def download_assessment_report(request: Request, token: str) -> Response:
    """Generate the complete governance report from persisted assessment results."""
    with SessionLocal() as session:
        assessment = get_active_assessment(session, token)
        ensure_assessment_access(session, assessment, request)

        agents = session.query(Agent).filter(Agent.assessment_id == assessment.id).all()

        results = []
        for agent in agents:
            result_record = (
                session.query(AgentResultRecord)
                .filter(AgentResultRecord.agent_id == agent.id)
                .first()
            )

            if result_record is None or not result_record.result_data:
                results.append(AgentResult(agent_name=agent.agent_name))
                continue

            result_data = dict(result_record.result_data)
            result_data.setdefault("agent_name", agent.agent_name)
            results.append(AgentResult.model_validate(result_data))

        tiers = ("Low", "Moderate", "High", "Critical")
        summary = {
            tier: sum(1 for result in results if result.tier == tier) for tier in tiers
        }

        portfolio = PortfolioResult(
            results=results,
            total_agents=len(results),
            summary=summary,
        )

        organization_name = "Organization not specified"
        organization_id = getattr(assessment, "organization_id", None)
        if organization_id:
            organization = (
                session.query(Organization)
                .filter(Organization.id == organization_id)
                .first()
            )
            if organization is not None:
                organization_name = organization.name

        assessment_id = assessment.id
        assessment_date = assessment.created_at.isoformat()

        report_html = render_governance_report(
            portfolio.model_dump_json(),
            organization_name=organization_name,
            assessment_id=assessment_id,
            assessment_date=assessment_date,
        )

    pdf_bytes = render_governance_report_pdf_bytes(report_html)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="agentguard_report_{token}.pdf"'
            )
        },
    )
