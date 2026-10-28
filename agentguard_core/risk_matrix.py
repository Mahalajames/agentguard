"""Generate a risk matrix image from AgentGuard portfolio results."""

from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from agentguard_core.models import PortfolioResult


def generate_risk_matrix_png(portfolio: PortfolioResult) -> bytes:
    """Return a PNG risk matrix plotting agents by severity and likelihood."""
    fig, ax = plt.subplots(figsize=(8, 7))

    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_xticks(range(1, 6))
    ax.set_yticks(range(1, 6))
    ax.set_xlabel("Likelihood (1 = lowest, 5 = highest)")
    ax.set_ylabel("Severity (1 = lowest, 5 = highest)")
    ax.set_title("AgentGuard Risk Matrix")
    ax.set_xticks([x + 0.5 for x in range(1, 5)], minor=True)
    ax.set_yticks([y + 0.5 for y in range(1, 5)], minor=True)
    ax.grid(which="minor", linewidth=1, color="gray", alpha=0.6)
    ax.tick_params(which="minor", bottom=False, left=False)

    tier_colors = {
        "Low": "#4caf50",
        "Moderate": "#ffca28",
        "High": "#ff9800",
        "Critical": "#e53935",
    }

    plotted = 0

    for index, agent in enumerate(portfolio.results, start=1):
        position = agent.matrix_position
        if not position:
            continue

        severity_value = position.get("severity")
        likelihood_value = position.get("likelihood")

        if severity_value is None or likelihood_value is None:
            continue

        severity = max(1, min(5, round(severity_value) + 1))
        likelihood = max(1, min(5, round(likelihood_value) + 1))

        ax.scatter(
            likelihood,
            severity,
            s=140,
            color=tier_colors.get(agent.tier, "#1976d2"),
            edgecolors="black",
            linewidths=0.7,
            zorder=3,
        )
        ax.annotate(
            str(index),
            (likelihood, severity),
            ha="center",
            va="center",
            fontsize=8,
            zorder=4,
        )
        plotted += 1

    if plotted == 0:
        ax.text(
            3,
            3,
            "No agents have complete matrix positions",
            ha="center",
            va="center",
            wrap=True,
        )

    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()

    image_buffer = BytesIO()
    fig.savefig(image_buffer, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    return image_buffer.getvalue()
