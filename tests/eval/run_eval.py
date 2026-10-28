"""Evaluate grounding validation across 20 synthetic portfolios."""

import json

from agentguard_core.llm_adapter import validate_narrative


def make_portfolio(portfolio_number: int, agent_count: int) -> dict:
    """Create a deterministic portfolio with unique finding IDs."""
    results = []

    for agent_number in range(agent_count):
        finding_id = f"F-P{portfolio_number:02d}-A{agent_number:02d}"
        results.append(
            {
                "agent_name": f"Evaluation Agent {agent_number + 1}",
                "findings": [
                    {
                        "id": finding_id,
                        "rule": "evaluation_rule",
                        "text": "A governance finding was identified.",
                    }
                ],
            }
        )

    return {
        "total_agents": agent_count,
        "summary": {},
        "results": results,
    }


def main() -> None:
    total_generated = 0
    total_retained = 0
    total_dropped = 0

    for portfolio_number in range(1, 21):
        agent_count = (portfolio_number % 5) + 1
        portfolio = make_portfolio(portfolio_number, agent_count)

        valid_ids = [result["findings"][0]["id"] for result in portfolio["results"]]

        sentences = [
            (
                f"Supported finding for agent {index + 1}. "
                f"[{valid_ids[index % len(valid_ids)]}]"
            )
            for index in range(20)
        ]

        # Add one deliberately uncited sentence to each portfolio.
        sentences.append("This sentence has no supporting citation.")

        narrative = {
            "executive_summary": sentences,
            "agent_explanations": [],
            "plan_30_60_90": [],
        }

        _, stats = validate_narrative(
            json.dumps(portfolio),
            json.dumps(narrative),
        )

        total_generated += stats.generated_sentences
        total_retained += stats.retained_sentences
        total_dropped += stats.dropped_sentences

        print(
            f"Portfolio {portfolio_number:02d}: "
            f"agents={agent_count}, "
            f"grounded_rate={stats.grounded_sentence_rate:.2%}, "
            f"drop_rate={stats.drop_rate:.2%}"
        )

    grounded_rate = total_retained / total_generated if total_generated else 1.0
    drop_rate = total_dropped / total_generated if total_generated else 0.0

    print("\nEvaluation totals")
    print("Portfolios: 20")
    print(f"Generated sentences: {total_generated}")
    print(f"Retained sentences: {total_retained}")
    print(f"Dropped sentences: {total_dropped}")
    print(f"Grounded sentence rate: {grounded_rate:.2%}")
    print(f"Drop rate: {drop_rate:.2%}")


if __name__ == "__main__":
    main()
