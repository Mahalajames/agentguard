# AgentGuard Framework Reading Notes

**Purpose:** Initial checks AgentGuard should consider when assessing AI agents, informed by the NIST AI Risk Management Framework (AI RMF), NIST AI 600-1, and the OWASP Top 10 for LLM Applications.

1. **Governance and accountability:** Check whether an organization has assigned responsibility for the AI agent, established policies for its use, and defined who is accountable when something goes wrong. *(NIST AI RMF — Govern)*

2. **Intended use and affected people:** Identify the agent's purpose, where it will be deployed, who may be affected by its decisions or actions, and what harms could result. *(NIST AI RMF — Map)*

3. **Autonomy and human oversight:** Assess whether the agent only makes recommendations or can independently take actions, use tools, or trigger other systems. Check whether human approval is required for consequential actions. *(OWASP — Excessive Agency)*

4. **Sensitive data protection:** Check what personal or confidential data the agent can access, how that data is protected, and whether it could be disclosed to unauthorized people. *(OWASP — Sensitive Information Disclosure; NIST AI 600-1)*

5. **Prompt injection and untrusted inputs:** Assess whether malicious instructions in user input, documents, or retrieved content could manipulate the agent or cause it to misuse tools or data. *(OWASP — Prompt Injection)*

6. **Reliability and information integrity:** Consider whether the agent could generate inaccurate or fabricated information and whether important outputs are checked before people rely on them. *(NIST AI 600-1)*

7. **Bias and unequal impact:** Check whether the agent could produce unfair outcomes for different groups, especially when used in consequential areas such as education, employment, or access to services. *(NIST AI 600-1; NIST AI RMF — Map and Measure)*

8. **Testing before deployment and after changes:** Check whether the organization tests expected behavior, risky edge cases, and adversarial inputs before deployment and after significant model, prompt, or configuration changes. *(NIST AI RMF — Measure)*

9. **Monitoring and incident response:** Check whether the organization monitors the agent after deployment, records important actions and failures, and has a process for investigating incidents and reducing recurring risks. *(NIST AI RMF — Manage)*

10. **Evidence, explainability, and unknowns:** Make each risk finding traceable to a written rule and supporting evidence. Identify unanswered questions, explain why a safeguard is recommended, and flag situations that require human review rather than presenting uncertain results as facts. *(NIST AI RMF — Govern, Measure, and Manage; AgentGuard design requirement)*

**Implementation note:** These are initial design considerations, not a finalized scoring rubric. Verify specific framework subcategories and citations before using them in AgentGuard's safeguard library.
