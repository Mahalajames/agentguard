
# AgentGuard Scoring Guide

## Purpose

AgentGuard evaluates AI agents across two areas: **risk** and **readiness**. Risk measures the potential harm an agent could cause, while readiness measures whether the organization has appropriate controls in place. The results help teams identify risks, prioritize safeguards, and decide where human oversight is needed.

## 1. Risk Score

AgentGuard evaluates six risk dimensions:

| Dimension | Weight | What it measures |
|---|---:|---|
| Autonomy level | 15% | How independently the agent can act |
| Data sensitivity | 15% | The sensitivity of information the agent can access |
| Financial authority | 15% | The agent's ability to make or affect financial decisions |
| Human oversight | 20% | How much effective human oversight is available |
| Affected population | 15% | The number or vulnerability of people potentially affected |
| Failure consequences | 20% | The severity of harm if the agent fails |

Each dimension contributes to the overall risk score according to its weight. Higher values represent greater risk, including higher values for the human-oversight dimension when oversight is weaker.

**Example:** An agent with substantial autonomy, access to sensitive data, and limited human oversight should generally receive a higher risk score than a tightly restricted agent with effective oversight.

If a required risk dimension is unknown, AgentGuard returns an unknown risk score rather than treating missing information as zero risk.

## 2. Risk Tiers

The numeric risk score maps to one of four tiers:

| Score | Tier |
|---:|---|
| 0–24 | Low |
| 25–49 | Moderate |
| 50–74 | High |
| 75–100 | Critical |

**Example:** A score of 58 is High risk. A score of 82 is Critical risk.

Risk tiers may be raised by red-line rules. A Low numeric score does not guarantee a Low final tier.

## 3. Red-Line Rules

Red-line rules identify conditions that require a higher risk classification regardless of the ordinary weighted score. These rules help prevent serious risks from being hidden by low scores in unrelated dimensions.

AgentGuard includes rules for especially sensitive data and combinations of financial authority, weak oversight, affected populations, and severe failure consequences.

**Example:** An agent that meets a Critical red-line condition is classified as Critical even if its numeric score would otherwise produce a lower tier.

## 4. Risk Matrix

AgentGuard also calculates a matrix position using likelihood and severity.

- **Likelihood** is based on autonomy and human oversight. Weaker oversight increases the likelihood rating.
- **Severity** considers failure consequences, affected populations, and the greater of financial authority or sensitive-data access.

The inputs are converted to matrix indices from 0 to 4 using the project's rounding rules.

**Example:** An agent with high autonomy and weak oversight may have a higher likelihood rating than an agent whose actions require effective human approval.

The matrix provides another way to understand risk; it complements rather than replaces the overall risk score and red-line rules.

## 5. Readiness Score

Readiness evaluates ten organizational controls:

1. Named owner
2. Data inventory
3. Scope limits
4. Logging
5. Kill switch
6. Review process
7. Testing
8. Incident plan
9. Vendor terms
10. Transparency

Each control uses a value from 0 to 2:

- **0:** The control is absent.
- **1:** The control is partially implemented.
- **2:** The control is fully implemented.

The readiness score is expressed as a percentage, with higher scores indicating stronger readiness.

**Example:** If all ten controls are fully implemented, readiness is 100%. If one control is unknown and the other nine are fully implemented, the score is 90%.

An unknown control is not treated as fully implemented. Teams should investigate unknown values rather than assuming a control exists.

## 6. Required Safeguards

AgentGuard compares an agent's profile with the safeguard library in `data/safeguards.csv`. Safeguards are selected when their trigger conditions match the profile.

Trigger conditions support the documented comparison operators and combined conditions, including `>=`, `==`, `!=`, `contains`, and `AND`. Conditions are evaluated by the project's safe condition parser, not by executing arbitrary Python expressions.

Unknown values are handled conservatively according to the trigger operator and parser rules.

**Example:** A high-autonomy agent can trigger safeguards intended to limit actions, validate outputs, or require additional review.

Each safeguard includes an identifier, trigger condition, safeguard description, framework mapping, priority, and effort information.

## 7. Human-Review Plan

AgentGuard generates a human-review plan to help teams decide where people should remain involved. The plan uses the assessed agent profile and applicable risk conditions to identify review needs.

**Example:** An agent that can make consequential decisions should have appropriate human review before high-impact actions are completed.

The plan is a practical recommendation, not a substitute for organizational approval or professional judgment.

## 8. Final Assessment Results

For each agent, AgentGuard produces a result that can include:

- Risk score and final tier
- Risk matrix position
- Triggered red-line rules
- Readiness score
- Required safeguards
- Findings with supporting evidence and framework references
- Human-review recommendations

These outputs are intended to make risk assessments understandable and actionable for nontechnical teams.

## 9. Important Limitations

AgentGuard's results depend on the accuracy and completeness of the information provided. Missing, incorrect, or outdated inputs can affect the assessment.

A score is a decision-support aid, not a guarantee of safety or compliance. Organizations should validate their inputs, review findings, implement appropriate safeguards, and revisit assessments when an agent or its operating environment changes.
