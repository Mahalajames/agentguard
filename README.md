
# AgentGuard

AI Agent Risk and Readiness Scanner

A free web tool that lets any organization describe the AI agents it is using or planning, then returns a Risk Score, a Readiness Score, a risk matrix, the safeguards it must put in place, a human-review plan, and a downloadable governance report written in plain language.

## Project Status

**Status:** Week 0 — Repository setup and project research in progress
**Last updated:** October 10, 2026

**Status:** Week 1 — Foundation and validation complete
**Last updated:** October 15, 2026

**Status:** Week 2 — Risk scoring engine, automated testing, and CLI complete
**Last updated:** October 19, 2026

## Project Overview

AgentGuard helps nonprofits, schools, clinics, and small businesses understand the risks of the AI agents they use or plan to deploy. It is designed to make responsible AI governance more accessible to organizations without dedicated governance teams.

## Scope Guardrails

### In Scope

- CSV or XLSX inventory uploads and a guided assessment.
- An explainable risk-scoring engine and readiness assessment.
- A library of recommended safeguards.
- A dashboard with a risk matrix and human-review recommendations.
- An AI-assisted narrative layer with evaluation.
- A downloadable PDF governance report.
- A live deployment, documentation, and a demonstration video.
- An English-language interface with plain-language explanations.

### Out of Scope

- Automatically scanning an organization's systems, logs, or accounts.
- Integrations with vendor platforms such as Salesforce, Microsoft, Google, Zapier, or OpenAI dashboards.
- User accounts, authentication, role-based access, billing, or multi-tenant features.
- Legal advice or compliance certification. AgentGuard is a governance aid, not legal counsel.
- Model fine-tuning, vector databases, or a chat interface.

### Core Design Principles

- **Explainable scoring:** Every risk flag must trace to a documented rule.
- **Human oversight:** Recommendations should identify where human review is needed.
- **Privacy-conscious design:** Users describe AI systems, not individual customers, students, or patients. Do not upload personal records.
- **Grounded AI writing:** The language model may explain existing findings but must not invent scores or introduce unsupported risks.

## Technology

The planned stack will be documented during project design. The initial direction is Python and Streamlit, subject to confirmation.

## License

The license will be added according to the terms of the fellowship agreement.

## Gate 3 — API Verification

Start the API and database:

```bash
docker compose up -d --build
