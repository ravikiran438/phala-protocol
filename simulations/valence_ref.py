# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Reproduces Figure 1 of the Phala paper.

Sensitivity of the reference valence formula to each of its three
signal components. The reference formula is:

    valence_ref = 0.5 * completion_latency_ratio
                + 0.3 * engagement_quality
                + 0.2 * explicit_rating_normalized

Run from the repository root:

    python simulations/valence_ref.py

Writes ``figures/valence_ref.png``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def valence_ref(clr: float, eq: float, ern: float) -> float:
    return 0.5 * clr + 0.3 * eq + 0.2 * ern


def main() -> None:
    x = np.linspace(-1.0, 1.0, 200)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=True)

    # Panel A: vary completion_latency_ratio
    ax = axes[0]
    for eq_val, color, label in (
        (0.0, "#e74c3c", "engagement=0"),
        (0.5, "#f39c12", "engagement=0.5"),
        (1.0, "#2ecc71", "engagement=1.0"),
    ):
        ax.plot(x, valence_ref(x, eq_val, 0.0), color=color, linewidth=2, label=label)
    ax.set_xlabel("completion_latency_ratio", fontsize=10)
    ax.set_ylabel("valence_ref", fontsize=11)
    ax.set_title("(a) Varying latency\n(explicit_rating=0)", fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.axhline(0, color="grey", linestyle=":", linewidth=0.8)
    ax.axvline(0, color="grey", linestyle=":", linewidth=0.8)
    ax.grid(True, alpha=0.3)

    # Panel B: vary engagement_quality
    ax = axes[1]
    for clr_val, color, label in (
        (-0.5, "#e74c3c", "latency=-0.5 (slow)"),
        (0.0, "#f39c12", "latency=0.0"),
        (0.8, "#2ecc71", "latency=0.8 (fast)"),
    ):
        ax.plot(x, valence_ref(clr_val, x, 0.0), color=color, linewidth=2, label=label)
    ax.set_xlabel("engagement_quality", fontsize=10)
    ax.set_title("(b) Varying engagement\n(explicit_rating=0)", fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.axhline(0, color="grey", linestyle=":", linewidth=0.8)
    ax.axvline(0, color="grey", linestyle=":", linewidth=0.8)
    ax.grid(True, alpha=0.3)

    # Panel C: vary explicit_rating on a 1-5 scale
    ratings = np.array([1, 2, 3, 4, 5])
    ern = (ratings - 3) / 2
    ax = axes[2]
    for eq_val, color, label in (
        (0.0, "#e74c3c", "engagement=0"),
        (0.5, "#f39c12", "engagement=0.5"),
        (1.0, "#2ecc71", "engagement=1.0"),
    ):
        v = valence_ref(0.5, eq_val, ern)
        ax.plot(ratings, v, "o-", color=color, linewidth=2, markersize=6, label=label)
    ax.set_xlabel("explicit_rating (1-5 scale)", fontsize=10)
    ax.set_title("(c) Varying explicit rating\n(latency_ratio=0.5)", fontsize=10)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.legend(fontsize=8, loc="lower right")
    ax.axhline(0, color="grey", linestyle=":", linewidth=0.8)
    ax.grid(True, alpha=0.3)

    fig.suptitle(
        "Reference Formula: valence_ref = 0.5*latency + 0.3*engagement + 0.2*rating",
        fontsize=12,
        y=1.02,
    )
    fig.tight_layout()

    out = Path(__file__).resolve().parent.parent / "figures" / "valence_ref.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
