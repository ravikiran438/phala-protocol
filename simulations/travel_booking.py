# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Reproduces Figure 5 of the Phala paper.

Agent-routing-weight convergence over 20 booking episodes in a
three-agent travel-booking chain. Panel A shows Agent A's routing
weights toward Agent B (reliable), Agent C (mediocre), and Agent D
(inconsistent). Panel B shows credit assignment by depth for a single
positive booking through the A -> B -> ToolServer chain with the
example from §3.8 (valence=0.814, eta=0.05).

Run:

    python simulations/travel_booking.py

Writes ``figures/travel_booking_learning.png``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


EPISODES = 20
ETA_BASE = 0.05
EXAMPLE_VALENCE = 0.814  # from §3.8


def simulate_routing_weights(seed: int = 42) -> tuple[list[float], list[float], list[float]]:
    """Simulate Agent A's routing weights over EPISODES bookings.

    Agent A (orchestrator, depth 0) routes to three specialist agents
    each episode and applies BeliefUpdate to its routing weights.
    """
    rng = np.random.default_rng(seed)

    # Simulated valence distributions (same as §3.8 narrative)
    valences_b = rng.uniform(0.7, 0.9, EPISODES)   # reliable
    valences_c = rng.uniform(0.2, 0.5, EPISODES)   # mediocre
    valences_d = rng.uniform(-0.3, 0.8, EPISODES)  # inconsistent

    w_b = [0.5]
    w_c = [0.5]
    w_d = [0.5]

    # Orchestrator is depth 0, so participation = 1.0
    p_a = 1.0
    for ep in range(EPISODES):
        w_b.append(float(np.clip(w_b[-1] + ETA_BASE * p_a * valences_b[ep], 0.0, 1.0)))
        w_c.append(float(np.clip(w_c[-1] + ETA_BASE * p_a * valences_c[ep], 0.0, 1.0)))
        w_d.append(float(np.clip(w_d[-1] + ETA_BASE * p_a * valences_d[ep], 0.0, 1.0)))

    return w_b, w_c, w_d


def main() -> None:
    w_b, w_c, w_d = simulate_routing_weights()
    eps = np.arange(0, EPISODES + 1)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(13, 5))

    # Panel A: routing weight evolution
    ax_a.plot(eps, w_b, "o-", color="#2ecc71", linewidth=2.2, markersize=5,
              label="Agent B (reliable)")
    ax_a.plot(eps, w_c, "s-", color="#f39c12", linewidth=2.2, markersize=5,
              label="Agent C (mediocre)")
    ax_a.plot(eps, w_d, "^-", color="#e74c3c", linewidth=2.2, markersize=5,
              label="Agent D (inconsistent)")
    ax_a.axhline(y=0.5, color="grey", linestyle=":", linewidth=1, alpha=0.5)
    ax_a.set_xlabel("Booking episode", fontsize=11)
    ax_a.set_ylabel("Routing weight (Agent A to callee)", fontsize=11)
    ax_a.set_title("(a) Routing Weight Evolution", fontsize=11)
    ax_a.legend(fontsize=9, loc="center right")
    ax_a.set_ylim(-0.05, 1.05)
    ax_a.grid(True, alpha=0.3)

    # Panel B: credit assignment by depth for a single positive booking
    chain_agents = ["Agent A\n(orchestrator)", "Agent B\n(travel search)", "Tool Server\n(airline API)"]
    chain_depths = [0, 1, 2]
    p_values = [1.0 / (1 + d) for d in chain_depths]
    deltas = [ETA_BASE * p * EXAMPLE_VALENCE for p in p_values]

    colors = ["#3498db", "#2ecc71", "#9b59b6"]
    bars = ax_b.bar(chain_agents, deltas, color=colors, alpha=0.85, width=0.5)
    for bar, delta, p in zip(bars, deltas, p_values, strict=True):
        ax_b.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.001,
            f"delta_w = {delta:.4f}\np = {p:.2f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax_b.set_ylabel("weight_delta", fontsize=11)
    ax_b.set_title(
        f"(b) Credit Assignment by Depth\n(valence={EXAMPLE_VALENCE}, eta={ETA_BASE})",
        fontsize=11,
    )
    ax_b.set_ylim(0, max(deltas) * 1.35)
    ax_b.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()

    out = Path(__file__).resolve().parent.parent / "figures" / "travel_booking_learning.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
