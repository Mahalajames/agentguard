
# AgentGuard

AI Agent Risk and Readiness Scanner

A free web tool that lets any organization describe the AI agents it is using or planning, then returns a Risk Score, a Readiness Score, a risk matrix, the safeguards it must put in place, a human-review plan, and a downloadable governance report written in plain language.

## Project Status

**Status:** Week 0 — Repository setup and project research in progress
**Last updated:** October 12, 2026

**Status:** Week 1 — Foundation and validation complete
**Last updated:** October 16, 2026

**Status:** Week 2 — Risk scoring engine, automated testing, and CLI complete
**Last updated:** October 23, 2026

**Status:** Week 3 — Backend, database, and deployment completed
**Last updated:** October 30, 2026

**Status:** Week 4 — Assessment workflow and results dashboard implemented
**Last updated:** November 6, 2026

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
```

Verify the API health endpoint:

```bash
curl -i http://localhost:8000/healthz
```

Expected response: HTTP 200 with {"status":"ok"}.




## Week 5 — Grounding Evaluation

The citation validator was evaluated against 20 synthetic portfolios
containing 1–5 agents each. Each portfolio included 21 generated test
sentences: 20 with valid finding citations and 1 intentionally uncited
sentence.

| Metric | Result | Target |
|---|---:|---:|
| Portfolios evaluated | 20 | 20 |
| Generated sentences | 420 | — |
| Retained sentences | 400 | — |
| Dropped sentences | 20 | — |
| Grounded sentence rate | 95.24% | 100% retained sentences grounded |
| Drop rate | 4.76% | <5% |

**Interpretation:** These are synthetic validator test results, not
measurements of real LLM-generated narrative quality. The validator
retained only sentences citing valid finding IDs and dropped the
intentionally uncited sentences. The grounded sentence rate is below
100% because the evaluation deliberately includes unsupported sentences.

Run the evaluation with:

```bash
python tests/eval/run_eval.py
```
