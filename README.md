# AgentGuard

**AI Agent Risk and Readiness Assessment**

AgentGuard is a web-based assessment tool that helps nonprofits, schools, clinics, and small businesses understand the risks of the AI agents they use or plan to deploy.

Users can describe an AI agent through a guided assessment or upload a CSV/XLSX inventory. AgentGuard evaluates risk and organizational readiness, identifies applicable safeguards, recommends human oversight, and produces a downloadable governance report.

> **Important:** AgentGuard is a decision-support and governance aid. It does not provide legal advice, certify compliance, or guarantee that an AI system is safe.

## Project Status

**Updated:** November 14, 2026

| Area | Status |
|---|---|
| Risk and readiness scoring | Implemented |
| CSV and XLSX inventory upload | Implemented |
| Guided assessment | Implemented |
| Dashboard and risk matrix | Implemented |
| Safeguards and human-review recommendations | Implemented |
| PDF governance report | Implemented |
| Methodology page and disclaimer | Implemented |
| User accounts and assessment history | Implemented |
| Automated tests | 78 passing |
| Synthetic grounding evaluation | Completed |
| Production deployment and monitoring | Pending verification |
| Screenshots and public demo | Pending |
| Anonymized pilot findings | Pending collection |

Features described as implemented have been developed and tested locally. This does not imply that a production deployment is live.

## Intended Users

- Nonprofit executive directors and program managers
- School and district administrators
- Clinic and healthcare operations leads
- Small-business owners
- Consultants supporting responsible AI adoption

AgentGuard aims to make practical AI governance accessible to organizations without dedicated AI risk or compliance teams.

## Features

### Assessment Inputs

- **Guided assessment:** Plain-language questions about an AI agent's risk profile and organizational controls. Unknown answers are allowed.
- **Inventory upload:** CSV or XLSX uploads using the AgentGuard template, with input validation.

### Assessment Outputs

- Risk score from 0–100 and corresponding risk tier
- Risk findings and triggered red-line rules
- Organizational readiness score
- Risk matrix positioning
- Recommended safeguards and framework references
- Human-review recommendations
- Prioritized actions
- Downloadable PDF governance report

### Accounts and Assessment History

- User signup, login, and logout
- Account assessment history
- Ability to claim a guest assessment
- Guest assessments expire after 24 hours
- Account assessments do not expire under the current application behavior

### Methodology and Transparency

The application includes a methodology page explaining the assessment approach and a disclaimer in the interface and downloadable report.

See [docs/scoring.md](docs/scoring.md) for the scoring methodology and [docs/methodology.md](docs/methodology.md) for supporting documentation.


## How the Assessment Works

1. A user submits an inventory or completes the guided assessment.
2. Input data is validated and converted into assessment models.
3. The scoring engine calculates risk and readiness results.
4. Risk rules and safeguard triggers identify relevant findings and recommendations.
5. Results are stored and displayed in the dashboard.
6. The report generator produces a downloadable PDF based on assessment results.

The scoring engine—not a language model—is responsible for calculating scores and applying risk rules. The Anthropic adapter is included in the codebase, but the standard assessment workflow should not be interpreted as a fully integrated, production LLM-generated narrative pipeline.

## Architecture

The application uses FastAPI and Jinja2 for the web interface, PostgreSQL for persistence, and a Python assessment core for deterministic scoring and safeguard matching. The API coordinates input validation, assessment storage, dashboard results, and PDF report generation.

### Main Code Areas

| Path | Responsibility |
|---|---|
| `agentguard_core/api.py` | FastAPI routes and application workflow |
| `agentguard_core/models.py` | Assessment data models |
| `agentguard_core/scoring.py` | Risk and readiness scoring |
| `agentguard_core/risk_matrix.py` | Risk matrix calculations |
| `agentguard_core/ingestion.py` | Inventory ingestion and validation |
| `agentguard_core/db_models.py` | SQLAlchemy database models |
| `agentguard_core/database.py` | Database connection and session setup |
| `agentguard_core/report.py` | Governance report generation |
| `agentguard_core/llm_adapter.py` | Anthropic integration adapter |
| `agentguard_core/cli.py` | Command-line interface |
| `agentguard_core/*.html` | Jinja2 interface templates |
| `templates/governance_report.html` | PDF report template |
| `migrations/` | Alembic database migrations |
| `data/` | Safeguard and failure-scenario reference data |
| `tests/` | Automated tests |

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI |
| Interface | Jinja2 and HTML templates |
| Database | PostgreSQL 16 |
| ORM and migrations | SQLAlchemy and Alembic |
| Data validation | Pydantic |
| Database driver | psycopg |
| Inventory processing | Python CSV support and openpyxl |
| PDF generation | WeasyPrint and ReportLab |
| LLM adapter | Anthropic Python SDK |
| Authentication | pwdlib with Argon2 password hashing |
| CLI | Typer |
| Containers | Docker and Docker Compose |
| Tests and code quality | pytest and Ruff |

## Local Development Setup

### Prerequisites

- Python 3.12
- Docker Desktop with Docker Compose
- Git


### 1. Clone the Repository

Clone the repository from GitHub and enter the project directory.

### 2. Create a Virtual Environment

Create and activate a Python 3.12 virtual environment.

### 3. Install Dependencies

Install the project and development dependencies using `python -m pip install -e ".[dev]"`.

### 4. Configure Environment Variables

Copy `.env.example` to `.env`. Set `DATABASE_URL` and `POSTGRES_PASSWORD` to use the same database password. `ANTHROPIC_API_KEY` is optional for the standard deterministic assessment workflow.

Never commit `.env` or expose API keys and database passwords.

### 5. Start PostgreSQL

Start the database service with `docker compose up -d db`.

### 6. Apply Database Migrations

Run `alembic upgrade head`.

### 7. Load Reference Data

Export the variables from `.env` into your shell, then run `python scripts_seed.py`.

### 8. Start the Application

Run `uvicorn agentguard_core.api:app --reload --host 127.0.0.1 --port 8000`.

Open the application at `http://127.0.0.1:8000`. Interactive API documentation is available at `/docs`.

### 9. Verify Application Health

Run `curl -i http://127.0.0.1:8000/healthz` in another terminal. A successful response returns HTTP 200 with `{"status":"ok"}`.

### Docker Notes

The PostgreSQL service maps host port `5433` to container port `5432`. The application uses port `8000`.

The full Docker stack can be started with `docker compose up -d --build`. Database migrations and reference-data seeding must still be performed explicitly.

Stop services with `docker compose down`. Do not use `docker compose down -v` unless you intentionally want to delete the database volume and its data.


## Command-Line Interface

AgentGuard includes a CLI for working with inventory files.

- `agentguard template` — generate the inventory template.
- `agentguard score inventory.csv --out results.json` — assess an inventory and write the results to JSON.

Use `agentguard --help` or `agentguard score --help` to view available options.

## Testing and Code Quality

Run the automated test suite:

    python -m pytest -q

Run Ruff checks:

    ruff check .
    ruff format --check .

Latest local verification (November 14, 2026):

- 78 automated tests passing.
- Ruff lint checks passing.
- Ruff formatting checks passing.

## Synthetic Grounding Evaluation

AgentGuard includes a synthetic evaluation of its finding-citation validation.

The evaluation used 20 synthetic portfolios containing 420 generated sentences:

- 400 supported sentences were retained.
- 20 intentionally unsupported sentences were dropped.
- Retention rate: 95.24%.
- Unsupported sentence drop rate: 4.76%.

Run the evaluation with `python tests/eval/run_eval.py`.

These results measure the citation validator against synthetic test data. They are not evidence of real-world model accuracy, organizational safety, or pilot effectiveness.


## Security, Limitations, and Responsible Use

AgentGuard is a decision-support tool, not a substitute for professional legal, compliance, security, or risk-management advice.

- Assessment results depend on the accuracy and completeness of user-provided information.
- AgentGuard does not automatically scan or inspect deployed AI systems.
- A risk score does not guarantee that an AI system is safe or compliant.
- Do not upload confidential, personally identifiable, or sensitive records during testing.
- Keep database credentials and API keys out of source control.
- Passwords are hashed using Argon2.

Production security review, monitoring, backup validation, and deployment verification remain outstanding.

## Documentation and Reference Files

Additional project documentation:

- [System design](docs/design.md)
- [Scoring methodology](docs/scoring.md)
- [Methodology documentation](docs/methodology.md)
- [AI impact assessment notes](docs/aia-notes.md)
- [CSV inventory template](data/agentguard_upload_template.csv)

An XLSX inventory template is also available in the `data/` directory.

## Deployment and Launch Status

The application has been developed and tested locally. Production deployment and public availability have not yet been verified.

Remaining launch work includes:

- Production deployment and public URL verification.
- Uptime monitoring and database backup verification.
- Application screenshots and a public demo.
- Anonymized pilot feedback and findings.
- A short product demonstration.
- A one-page case study.
- Project handoff documentation and launch review.

Pilot findings and production performance will be documented after they have been collected and verified.

## Contributing

Contributions and feedback are welcome. Please run the automated tests and Ruff checks before submitting changes.

The project's license and distribution terms are pending confirmation. No open-source license is currently asserted.
