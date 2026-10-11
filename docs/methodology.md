# AgentGuard Risk and Readiness Methodology

## 1. Purpose

This document defines how AgentGuard evaluates the risks associated with AI agents and an organization's readiness to govern them.

AgentGuard is a governance aid designed to help nonprofits, schools, clinics, and small businesses understand AI agent risks and identify practical safeguards. It is not legal advice or a compliance certification.

The methodology uses documented rules to produce explainable, repeatable results. Each risk finding must be traceable to a defined rule, and recommendations must be linked to the findings that justify them.

## 2. Assessment Overview

AgentGuard evaluates two separate areas:

* **Agent Risk:** The potential risk associated with an AI agent's purpose, capabilities, access, autonomy, and effects on people or organizational operations.
* **Organizational Readiness:** The extent to which an organization has the policies, controls, oversight, and response procedures needed to govern its AI agents.

These assessments are related but distinct. An organization may have strong governance practices while operating a high-risk agent, or it may operate a lower-risk agent without sufficient safeguards.

AgentGuard will present the results in plain language so that users can understand the findings and take practical next steps.

## 3. Methodology Principles

1. **Explainability:** Every risk finding must be linked to a documented rule.
2. **Consistency:** The same inputs must produce the same scoring results.
3. **Separation of scores:** Agent Risk and Organizational Readiness must be calculated separately.
4. **Transparency:** Unknown or missing information must be identified rather than silently treated as confirmed.
5. **Actionability:** Findings must connect to relevant safeguards and human-review recommendations.
6. **Human oversight:** AgentGuard supports governance decisions; it does not replace professional judgment or organizational accountability.

## 4. Scoring and Recommendations

The detailed scoring dimensions, level definitions, weights, red-line rules, tier thresholds, readiness controls, and human-review requirements are defined in the sections that follow.

Risk scoring and safeguard matching will use deterministic rules. A large language model may help translate findings into plain-language explanations, but it must not calculate risk scores, invent findings, or independently determine an agent's risk tier.

## 5. Risk Dimensions and Levels

Each AI agent is evaluated across six dimensions. Each dimension receives a score from 0 to 4, where higher values generally indicate greater risk. Human oversight is an inverted dimension: a higher score means weaker oversight.

The weights below are taken from the project brief. Levels 1 and 3 are proposed intermediate definitions between the brief's level 0, 2, and 4 anchors. These intermediate definitions must be reviewed with Benjamin before the scoring engine is implemented.

### 5.1 Autonomy — Weight: 0.15

Measures how independently the agent can plan and execute actions.

* **Level 0:** Drafts or suggests only; a human performs every action.
* **Level 1:** Prepares actions for a human to approve before execution.
* **Level 2:** Executes routine actions without per-action approval, inside fixed rules.
* **Level 3:** Executes multi-step tasks within defined boundaries, with some checkpoints.
* **Level 4:** Plans multi-step work, chooses its own tools, can trigger other agents, and has no checkpoints.

### 5.2 Sensitive Data Access — Weight: 0.15

Measures the sensitivity of the information the agent can access.

* **Level 0:** No personal data.
* **Level 1:** Internal, non-sensitive organizational information only.
* **Level 2:** Basic personal data, such as names and contact details.
* **Level 3:** Sensitive personal data, such as financial information or confidential records.
* **Level 4:** Special-category data, including health information, immigration status, minors' data, biometrics, criminal justice information, or precise location.

### 5.3 Financial Authority — Weight: 0.15

Measures the agent's ability to move money or change financial arrangements.

* **Level 0:** No financial authority.
* **Level 1:** Can prepare financial actions but cannot execute them.
* **Level 2:** Executes small transactions under a hard cap with logging.
* **Level 3:** Can execute significant transactions under limits or change financial records with limited restrictions.
* **Level 4:** Can perform uncapped financial actions, move funds between accounts, or change payroll, billing, or benefits.

### 5.4 Human Oversight, Inverted — Weight: 0.20

Measures how much human review and control exists. Higher levels mean less oversight.

* **Level 0:** A human approves every action before it happens.
* **Level 1:** A human approves consequential actions and reviews routine actions regularly.
* **Level 2:** A human reviews a sample after the fact, weekly.
* **Level 3:** Review is infrequent, limited, or does not reliably cover consequential actions.
* **Level 4:** No defined review process or no named owner.

### 5.5 Affected Populations — Weight: 0.15

Measures who may be affected by the agent's actions and decisions.

* **Level 0:** Internal staff only; no decisions about people.
* **Level 1:** Limited internal operational effects, with no meaningful consequences for individuals.
* **Level 2:** General public or informational interactions.
* **Level 3:** People may be affected in consequential ways, but the most vulnerable groups are not the primary affected population.
* **Level 4:** Vulnerable groups—including children, students, patients, immigrants, benefit applicants, or people in crisis—face consequential outcomes.

### 5.6 Failure Consequences — Weight: 0.20

Measures the severity of harm if the agent fails or acts incorrectly.

* **Level 0:** Minor inconvenience that is instantly reversible.
* **Level 1:** Limited disruption that can be corrected quickly with little lasting impact.
* **Level 2:** Financial loss or data exposure recoverable within days.
* **Level 3:** Serious financial, privacy, operational, or personal harm that is difficult to reverse.
* **Level 4:** Irreversible harm to a person, a safety risk, legal liability, or an existential loss for the organization.

## 6. Risk Score Calculation

The Risk Score is calculated using a weighted sum of the six dimension scores.

For each dimension, multiply its weight by its level divided by 4. Add the six results and multiply the total by 100.

**Formula:**

Risk Score = 100 × Σ (dimension weight × dimension level ÷ 4)

The result ranges from 0 to 100. A higher score indicates greater assessed risk.

Red-line rules may override the calculated score and raise an agent's assigned tier. The final tier is therefore determined by both the weighted Risk Score and any applicable red-line rules.

## 7. Red-Line Rules

Red-line rules identify combinations of risk factors that require a higher tier regardless of the weighted Risk Score.

### 7.1 Automatic Critical Tier

An agent is automatically assigned the Critical tier if any of these conditions is met:

1. **Financial authority and weak oversight:** Financial authority is level 3 or higher, and human oversight is level 3 or higher.
2. **Consequential decisions affecting vulnerable populations:** Affected populations are level 4, failure consequences are level 3 or higher, and human oversight is level 2 or higher.
3. **Sensitive data and high autonomy:** Sensitive data access is level 4, and autonomy is level 3 or higher.

### 7.2 Automatic High Tier

An agent is automatically assigned at least the High tier if either condition is met:

1. Financial authority is level 3 or higher, and human oversight is level 2.
2. Affected populations >= 3, failure consequences >= 3, and human oversight >= 2.


### 7.3 Missing Accountable Owner

An agent without a named accountable owner cannot be assigned the Low tier.

### 7.4 Rule Precedence

The highest applicable tier takes precedence. An automatic Critical result cannot be lowered by a weighted score, and an automatic High result cannot be lowered below High by a weighted score.

All triggered rules must be recorded with a rule ID and a plain-language explanation so users can understand why the tier was assigned.

## 8. Risk Tiers and Human-Review Requirements

### Low — Risk Score 0–24

**Reference point:** EU AI Act minimal risk.

* Name an accountable owner.
* Review a monthly sample of 5% of agent actions.
* Reassess annually.

### Moderate — Risk Score 25–49

**Reference point:** EU AI Act limited risk.

* Review a weekly sample of 10% of agent actions.
* Escalate exceptions.
* Require pre-action approval for consequential actions.
* Reassess every six months.

### High — Risk Score 50–74

**Reference point:** EU AI Act high-risk obligations.

* Require pre-action approval for all consequential actions.
* Review a daily sample of routine actions.
* Assign a designated reviewer with budgeted review time.
* Conduct quarterly audits and reassessments.

### Critical — Risk Score 75–100

**Reference point:** Do not deploy as configured.

* Redesign the agent before deployment.
* Reduce autonomy or financial authority.
* Add pre-action approval for every action affecting people or money.
* Reassess the agent after changes.

### 8.1 Final Tier Assignment

The initial tier is determined by the weighted Risk Score. AgentGuard then evaluates all red-line rules and the missing-owner rule. The final tier must be at least as severe as the highest tier required by any applicable rule.

A red-line override may therefore produce a final tier higher than the numerical Risk Score alone would indicate.

## 9. Organizational Readiness Controls

Organizational readiness measures whether an organization has the safeguards, processes, and accountability needed to operate an AI agent responsibly. It is scored separately from Agent Risk.

Each of the ten controls receives a score of 0, 1, or 2.

* **0 — Absent or unknown:** The control is missing, there is no evidence that it exists, or its status cannot be verified.
* **1 — Partial:** The control exists in some form but is incomplete, inconsistently applied, or not fully tested.
* **2 — In place and tested:** The control is implemented, documented where appropriate, and supported by evidence that it has been tested or verified.

An unknown control receives a score of 0 until its status can be verified. The system should preserve whether a zero means *absent* or *unknown* so users can distinguish missing safeguards from missing information.

### 9.1 The Ten Readiness Controls

| ID    | Control                            | Absent or unknown (0)                                                                | Partial (1)                                                                                                  | In place and tested (2)                                                                                                                   |
| ----- | ---------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| RC-01 | Accountable owner and purpose      | No named accountable owner or written purpose statement can be verified.             | An owner or purpose statement exists, but one is missing, unclear, or outdated.                              | A named owner and current written purpose statement are documented.                                                                       |
| RC-02 | Data inventory and least privilege | Accessible data is not inventoried, or least-privilege access cannot be verified.    | Some data access is documented, but the inventory or access restrictions are incomplete.                     | Read/write access is inventoried, least-privilege permissions are configured, and access has been verified.                               |
| RC-03 | Enforced action limits             | Tool permissions and action limits are absent or cannot be verified.                 | Some restrictions exist, but they are incomplete or rely on prompts rather than enforced controls.           | Tool allow-lists, transaction caps, and applicable rate limits are enforced through code or configuration and tested.                     |
| RC-04 | Logging and audit trail            | Actions are not logged, or logging and retention cannot be verified.                 | Some actions are logged, but coverage, retention, or auditability is incomplete.                             | Every agent action has an auditable log, with a defined retention period that is implemented.                                             |
| RC-05 | Kill switch and rollback           | No kill switch or rollback procedure can be verified.                                | A procedure exists, but it has not been tested or cannot reliably stop or reverse relevant actions.          | The kill switch and applicable rollback procedure have been tested, with results documented.                                              |
| RC-06 | Human review process               | No defined reviewer or review process exists.                                        | A reviewer or process exists, but the cadence, sample rate, or allocated time is unclear or incomplete.      | A named reviewer, review cadence, sample rate, and time allocation are defined and followed.                                              |
| RC-07 | Pre-deployment testing             | No documented evaluation or failure testing can be verified.                         | Some tests exist, but golden cases, adversarial prompts, or failure drills are incomplete.                   | Pre-deployment evaluation includes golden cases, adversarial prompts, and relevant failure drills, with results recorded.                 |
| RC-08 | Incident response and notification | No incident response or notification plan can be verified.                           | A plan exists but does not clearly define responsible people, notification recipients, or timing.            | A documented plan identifies who responds, who is notified, and when notifications occur.                                                 |
| RC-09 | Vendor and model terms             | Relevant vendor or model terms have not been reviewed, or review cannot be verified. | Some terms have been reviewed, but data use, retention, training, or model-change notices remain unresolved. | Relevant terms covering data use, retention, training on organizational data, and model-change notices have been reviewed and documented. |
| RC-10 | Transparency and appeal            | No notice or human appeal process can be verified where people are affected.         | Notice, explanations, or an appeal channel exists but is incomplete or difficult to access.                  | Affected people receive notice of agent involvement, can request an explanation, and have access to a human appeal channel.               |

### 9.2 Readiness Score

The maximum readiness score is 20 points.

**Formula:**

`Readiness Score = (Total Control Points / 20) × 100`

The resulting score ranges from 0 to 100. It measures the documented implementation of organizational safeguards and must not be combined with the Agent Risk score into a single score unless a later, explicitly approved methodology defines how to do so.

### 9.3 Required Safeguards

AgentGuard identifies missing or partial readiness controls and applicable safeguards from the safeguard catalog. Required safeguards are presented in priority order, with an explanation of the associated risk or readiness gap.

Recommendations should identify the action needed, its priority, and its estimated effort. Unknown status should be clearly labeled so users know when further verification is needed.

Readiness scores and recommendations support decision-making; they do not independently certify that an AI agent is safe or compliant.

## 10. Risk Matrix

AgentGuard generates a 5×5 risk matrix to help users visualize the relationship between an agent’s likelihood index and severity index. Both indices range from 0 to 4.

### 10.1 Likelihood Index

The likelihood index is calculated from the agent’s autonomy and human oversight scores.

**Formula:**

`Likelihood Index = round((Autonomy + Human Oversight) / 2)`

Human oversight uses the inverted scale defined in Section 5: a higher score means less effective oversight and therefore greater risk.

### 10.2 Severity Index

The severity index is calculated from failure consequences, affected populations, and the greater of financial authority or sensitive data access.

**Formula:**

`Severity Index = round((Failure Consequences + Affected Populations + max(Financial Authority, Sensitive Data Access)) / 3)`

### 10.3 Matrix Interpretation

Each agent is placed into one of the 25 cells using its likelihood index and severity index.

* **Likelihood index (0–4):** The horizontal or vertical axis representing the likelihood-related index calculated from autonomy and oversight.
* **Severity index (0–4):** The other axis representing the severity-related index calculated from consequences, affected populations, and the greater of financial authority or sensitive data access.
* **Portfolio view:** When multiple agents are assessed, the matrix shows how they are distributed across the 25 cells, helping organizations identify concentrations of higher-risk agents.

The matrix supplements the weighted Agent Risk score; it does not replace the scoring formula, red-line rules, or final risk tier.

The matrix should display the index values and the number of agents in each cell. Agent details should be available so users can identify which assessments contribute to each cell.

### 10.4 Rounding and Missing Values

**Rounding:** Risk-matrix indices are rounded to the nearest whole number. When a value falls exactly halfway between two integers, it is rounded up.

**Unknown values:** Unknown inputs remain explicitly marked as unknown and are never silently treated as level 0. If an input required to calculate the risk matrix is unknown, AgentGuard will not assign a final matrix position. The report will identify the missing information and request follow-up assessment.

Red-line rules will still be evaluated using the available information. Unknown values will not cancel any red-line rule that has been triggered by known values. The report will clearly distinguish confirmed findings from unresolved questions.

These are proposed methodology decisions for review with Benjamin before implementation. They are intended to make uncertainty transparent and prevent incomplete information from creating a misleading impression of safety.


## 11. Human Review and Oversight

AgentGuard provides decision support, not an automated approval of an AI agent for deployment. Organizations remain responsible for reviewing results and deciding what actions to take.

| Risk Tier | Required Human Review                                                                                                                                                                                        |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Low       | A named owner conducts monthly reviews of a 5% sample of agent activity. Reassess annually.                                                                                                                  |
| Moderate  | Review a 10% sample weekly, escalate exceptions, and require pre-action approval for consequential actions. Reassess semi-annually.                                                                          |
| High      | Require pre-action approval for all consequential actions, conduct daily sample reviews of routine actions, and assign a designated reviewer with budgeted time. Conduct quarterly audits and reassessments. |
| Critical  | Do not deploy the agent as configured. Redesign it, reduce autonomy or financial authority, require pre-action approval for every action affecting people or money, and reassess before deployment.          |

The review requirements above are minimum recommendations associated with each tier. A triggered red-line rule may require a higher tier than the weighted score alone indicates.

## 12. LLM-Assisted Reporting and Safeguards

### 12.1 Separation of Responsibilities

The scoring engine is the authoritative source for scores, risk tiers, red-line results, missing controls, and safeguard recommendations. These results are calculated using deterministic rules.

The LLM adapter receives only structured output from the scoring engine. It must not receive raw uploaded assessment files, independently calculate risk scores, assign risk tiers, invent red-line findings, or create safeguards that are not present in the structured results.

The LLM may help communicate verified findings in plain language.

### 12.2 Permitted LLM Outputs

The LLM may generate:

* An executive summary of the assessment.
* A plain-language “what this means for you” paragraph for each assessed agent.
* A 30/60/90-day action plan based on the existing findings and safeguard recommendations.

Generated recommendations must remain consistent with the structured assessment results.

### 12.3 Finding-ID Traceability

Every sentence generated by the LLM must cite one or more valid finding IDs from the scoring engine’s structured output.

The reporting system must validate citations before displaying generated text:

1. Check that every cited finding ID exists in the structured results.
2. Remove any sentence that has no finding-ID citation.
3. Record the proportion of generated sentences that pass the grounding check.
4. Publish the grounded-sentence rate in the project README.

The grounded-sentence rate is a traceability measure. It does not, by itself, prove that a sentence is accurate or that an assessment is complete.

### 12.4 Human Responsibility

LLM-generated reports are explanatory summaries of the deterministic assessment, not independent risk judgments. Users should be able to inspect the underlying scores, triggered rules, missing controls, and safeguard records supporting each report.

Human reviewers remain responsible for evaluating the results, resolving unknowns, and deciding whether an agent is appropriate for its intended use.
