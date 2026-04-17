# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Reproduces Figure 2 of the Phala paper.

Participation-weighted update under three decay functions (uniform,
harmonic, exponential). The script verifies the numerical claims in
paper §3.5:

    harmonic(d=7) = 1/8  = 0.125   (12.5%)
    exponential(d=7) = 0.5^7 ≈ 0.0078 (0.8%)
    uniform(d=7) = 1/8 = 0.125

and plots participation strength plus resulting weight_delta under
η=0.05, valence=0.8 for each scheme.

Run:

    python simulations/participation_weight.py

Writes ``figures/participation_weight.png``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ETA_BASE = 0.05
EXAMPLE_VALENCE = 0.8


def uniform(depths: np.ndarray) -> np.ndarray:
    return np.full(len(depths), 1.0 / len(depths))


def exponential(depths: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    return alpha ** depths


def harmonic(depths: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + depths)


def main() -> None:
    depths = np.arange(0, 8)

    u = uniform(depths)
    e = exponential(depths)
    h = harmonic(depths)

    # Numerical sanity checks (reported in paper §3.5)
    assert np.isclose(h[7], 1.0 / 8), f"harmonic(d=7) should be 0.125, got {h[7]}"
    assert np.isclose(e[7], 0.5**7), f"exponential(d=7) should be {0.5**7}, got {e[7]}"
    print(f"harmonic(d=7) = {h[7]:.4f}  ({h[7]*100:.1f}%)")
    print(f"exponential(d=7) = {e[7]:.4f}  ({e[7]*100:.1f}%)")

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(12, 5))

    bar_width = 0.25

    # Panel A: participation strength p(i) by depth
    ax_a.bar(
        depths - bar_width, u, bar_width, color="#95a5a6", label="Uniform (1/n)", alpha=0.85
    )
    ax_a.bar(depths, h, bar_width, color="#2ecc71", label="Harmonic 1/(1+d)", alpha=0.85)
    ax_a.bar(
        depths + bar_width,
        e,
        bar_width,
        color="#e74c3c",
        label="Exponential 0.5^d",
        alpha=0.85,
    )
    ax_a.set_xlabel("Agent depth in invocation chain", fontsize=11)
    ax_a.set_ylabel("Participation strength p(i)", fontsize=11)
    ax_a.set_title("(a) Participation Decay Functions", fontsize=11)
    ax_a.set_xticks(depths)
    ax_a.set_xticklabels([f"d={d}" for d in depths])
    ax_a.legend(fontsize=9)
    ax_a.grid(True, alpha=0.3, axis="y")

    # Panel B: resulting weight_delta
    du = ETA_BASE * u * EXAMPLE_VALENCE
    dh = ETA_BASE * h * EXAMPLE_VALENCE
    de = ETA_BASE * e * EXAMPLE_VALENCE

    ax_b.bar(depths - bar_width, du, bar_width, color="#95a5a6", label="Uniform", alpha=0.85)
    ax_b.bar(depths, dh, bar_width, color="#2ecc71", label="Harmonic (Phala)", alpha=0.85)
    ax_b.bar(depths + bar_width, de, bar_width, color="#e74c3c", label="Exponential", alpha=0.85)
    ax_b.set_xlabel("Agent depth in invocation chain", fontsize=11)
    ax_b.set_ylabel("weight_delta", fontsize=11)
    ax_b.set_title(
        f"(b) Resulting Weight Updates (valence={EXAMPLE_VALENCE}, eta={ETA_BASE})",
        fontsize=11,
    )
    ax_b.set_xticks(depths)
    ax_b.set_xticklabels([f"d={d}" for d in depths])
    ax_b.legend(fontsize=9)
    ax_b.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()

    out = Path(__file__).resolve().parent.parent / "figures" / "participation_weight.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
