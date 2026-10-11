# AgentGuard Design

## 1. Problem and Purpose

AgentGuard is a free web-based tool that helps organizations assess the risks and readiness of the AI agents they use or plan to use.

AI agents can access sensitive information, make decisions, send communications, and take actions through other software. Nonprofits, schools, clinics, and small businesses may use these systems without having dedicated AI governance teams. When an agent fails, the consequences can affect finances, privacy, access to services, and people's opportunities.

AgentGuard aims to make AI risk assessment understandable and practical for organizations without specialized technical or governance staff. It provides consistent risk scores, recommended safeguards, and clear next steps.

## 2. Intended Users

**Primary users**

* Executive directors and program managers at nonprofits.
* School and district administrators.
* Clinic operations leads.
* Small-business owners.

**Secondary users**

* Boards and funders.
* Consultants advising organizations on responsible AI.

The interface and reports will use plain language so nontechnical users can understand the results and act on them.

## 3. Input Modes

AgentGuard supports two ways to describe an AI agent.

### Mode A: Inventory Upload

Users upload a CSV or XLSX file based on the AgentGuard template. Each row represents one AI agent. The application validates the file, identifies missing or invalid values, and assesses each agent using the defined scoring methodology.

### Mode B: Guided Assessment

Users answer approximately 16 plain-language questions about an AI agent: six questions about risk and ten about readiness. Unknown answers are allowed so users are not forced to guess.

**Privacy rule:** AgentGuard assesses information about systems, not individual people. Users must not upload customer, student, patient, or other personal records.

## 4. Outputs

For each assessed agent, AgentGuard will provide:

* A Risk Score from 0 to 100 and a risk tier.
* A list of identified risks and the rules behind them.
* Required safeguards with relevant framework references.
* Human-review recommendations.
* A portfolio Readiness Score.
* A 5-by-5 risk matrix.
* A prioritized 30/60/90-day action plan.
* A downloadable PDF governance report written in plain language.

The report is a governance aid, not legal advice or compliance certification.

## 5. Architecture

The application separates deterministic assessment logic from the interface, data storage, and language-model features.

```text
CSV/XLSX Upload ──┐
                  ├──> Streamlit Front End
Guided Assessment ┘             |
                                v
                           FastAPI
                                |
                                v
                      AgentGuard Core Package
                      - Input validation
                      - Risk scoring
                      - Readiness scoring
                      - Red-line rules
                      - Safeguard matching
                      - Human-review planning
                                |
                    ┌───────────┴───────────┐
                    v                       v
               PostgreSQL              Findings JSON
                    |                       |
                    v                       v
             Safeguard Library         LLM Adapter
                                            |
                                            v
                                      Report Generator
                                      - Jinja2 templates
                                      - WeasyPrint PDF
```

The core package will contain the deterministic assessment logic and must work independently of the API, database, and LLM. Every risk flag must trace to a written rule and its supporting evidence.

The LLM will explain existing findings in plain language and draft report narratives. It must not calculate scores, invent risks, or make unsupported claims. Generated statements must be linked to finding IDs and checked before inclusion in a report.

## 6. Technology Stack

| Layer               | Choice                                             | Justification                                                                                   |
| ------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Language            | Python 3.12                                        | Supports the project's data processing, assessment logic, and web application.                  |
| Data models         | Pydantic v2                                        | Validates inputs and defines consistent structures between components.                          |
| CSV/XLSX processing | pandas and openpyxl                                | Supports inventory uploads and spreadsheet handling.                                            |
| Core assessment     | Python package                                     | Keeps scoring deterministic, testable, and independent of external services.                    |
| API                 | FastAPI with Uvicorn                               | Provides structured endpoints and automatic API documentation.                                  |
| Front end           | Streamlit                                          | Allows a usable interface to be built quickly without a separate React application.             |
| Database            | PostgreSQL with SQLAlchemy and Alembic             | Stores structured safeguard data and supports schema changes.                                   |
| Local development   | SQLite where appropriate                           | Makes early local development simpler; PostgreSQL will be used for staging and production.      |
| Charts              | Plotly                                             | Supports the risk matrix, readiness gauge, and portfolio summaries.                             |
| Reports             | Jinja2 and WeasyPrint                              | Generates consistent HTML and downloadable PDF reports.                                         |
| LLM                 | Claude through the Anthropic Python SDK            | Drafts explanations from existing findings; deterministic code remains responsible for scoring. |
| Testing and quality | pytest, Ruff, pre-commit, pip-audit                | Supports automated tests, code quality, consistent commits, and dependency checks.              |
| Containers and CI   | Docker and GitHub Actions                          | Makes the application easier to run consistently and checks code on pushes.                     |
| Hosting             | Render or Railway with Neon or Supabase PostgreSQL | Provides a practical deployment path using managed hosting and a managed database.              |

## 7. Scope Guardrails

### In Scope

* Both input modes, the scoring engine, the safeguard library, the dashboard, the LLM narrative layer with evaluation, the PDF report, a live deployment, documentation, and a demo video.
* English-language interface and report. Plain-language wording tested with non-technical pilot users.

### Out of Scope

* Automated scanning of an organization's actual systems, logs, or accounts. AgentGuard assesses what people tell it about an agent.
* Integrations with vendor platforms (Salesforce, Microsoft, Google, Zapier, OpenAI dashboards).
* User accounts, authentication, role-based access, billing, or multi-tenant features.
* Legal advice or compliance certification. The report states clearly that it is a governance aid, not legal counsel.
* Model fine-tuning, vector databases, or a chat interface.

### Stretch Items

Only if the project is ahead of schedule:

* Spanish-language report output.
* A vendor questionnaire importer that pre-fills the template from a vendor's security questionnaire.
* Re-assessment comparison: upload a second inventory and see what changed.

## 8. Core Design Principles

1. **Explainability:** Every score and risk flag must be traceable to a written rule.
2. **Separation of responsibilities:** Deterministic code calculates scores; the LLM only explains supported findings.
3. **Privacy:** Assess systems rather than personal records, and minimize the data sent to the LLM.
4. **Human oversight:** Higher-risk uses receive stronger human-review recommendations.
5. **Actionable results:** Recommendations should identify practical safeguards and prioritized next steps.
6. **Testability:** Synthetic profiles and automated tests will check scoring, red lines, and required safeguards.

## 9. Implementation Note

This document describes the planned design. Technology integrations, security controls, scoring rules, and deployment behavior must be verified during implementation and testing. Any significant change to the design should be documented and reviewed with the project supervisor.
