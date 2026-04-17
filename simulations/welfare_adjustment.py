# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Reproduces Figures 3 and 4 of the Phala paper.

Figure 3: welfare_adjustment over 12 weeks for three principal
trajectories (rising autonomy, stable baseline, declining autonomy
with rising load).

Figure 4: full parameter-space heatmap of welfare_adjustment as a
function of autonomy_index and load_ratio.

The formula (paper §3.6) is:

    welfare_adjustment(WT) = clip(
        1.0
        - 0.9 * max(0.0, density_adj - 1.0)
        + 2.0 * max(0.0, autonomy_index - 0.5),
        0.1, 2.0
    )

Run:

    python simulations/welfare_adjustment.py

Writes ``figures/welfare_over_time.png`` and ``figures/welfare_heatmap.png``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np


FLOOR = 0.1
CEILING = 2.0


def welfare_adjustment(
    autonomy_index: np.ndarray,
    load_ratio: np.ndarray,
    density_ratio: float | np.ndarray = 1.0,
) -> np.ndarray:
    density_adj = load_ratio / np.maximum(1.0, density_ratio)
    return np.clip(
        1.0
        - 0.9 * np.maximum(0.0, density_adj - 1.0)
        + 2.0 * np.maximum(0.0, autonomy_index - 0.5),
        FLOOR,
        CEILING,
    )


def plot_over_time(out_dir: Path) -> None:
    weeks = np.arange(1, 13)

    auto_rising = np.linspace(0.3, 0.8, 12)
    load_rising = np.ones(12)

    auto_stable = np.full(12, 0.5)
    load_stable = np.ones(12)

    auto_decline = np.linspace(0.6, 0.2, 12)
    load_decline = np.linspace(1.0, 1.8, 12)

    wa_rising = welfare_adjustment(auto_rising, load_rising)
    wa_stable = welfare_adjustment(auto_stable, load_stable)
    wa_decline = welfare_adjustment(auto_decline, load_decline)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(weeks, wa_rising, "o-", color="#2ecc71", linewidth=2.2, markersize=5,
            label="Rising autonomy (gaining independence)")
    ax.plot(weeks, wa_stable, "s--", color="#3498db", linewidth=2.2, markersize=5,
            label="Stable (baseline)")
    ax.plot(weeks, wa_decline, "^-", color="#e74c3c", linewidth=2.2, markersize=5,
            label="Declining autonomy + rising load")
    ax.axhline(y=1.0, color="grey", linestyle=":", linewidth=1, alpha=0.6)
    ax.text(12.2, 1.0, "baseline", va="center", fontsize=8, color="grey")
    ax.set_xlabel("Week", fontsize=11)
    ax.set_ylabel("welfare_adjustment", fontsize=11)
    ax.set_title(
        "Welfare Adjustment Over Time, Three Principal Trajectories",
        fontsize=12,
        pad=12,
    )
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    ax.set_ylim(0.0, 2.15)
    ax.set_xlim(0.5, 12.5)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(0.5))
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    out = out_dir / "welfare_over_time.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


def plot_heatmap(out_dir: Path) -> None:
    ai_range = np.linspace(0.0, 1.0, 100)
    lr_range = np.linspace(0.5, 3.0, 100)
    AI, LR = np.meshgrid(ai_range, lr_range)
    WA = welfare_adjustment(AI, LR)

    fig, ax = plt.subplots(figsize=(7, 5.5))
    im = ax.imshow(
        WA,
        origin="lower",
        aspect="auto",
        extent=[0.0, 1.0, 0.5, 3.0],
        cmap="RdYlGn",
        vmin=FLOOR,
        vmax=CEILING,
    )
    cbar = fig.colorbar(im, ax=ax, label="welfare_adjustment", shrink=0.85)
    cbar.set_ticks([0.1, 0.5, 1.0, 1.5, 2.0])

    cs = ax.contour(
        AI, LR, WA, levels=[0.1, 0.5, 1.0, 1.5, 2.0], colors="black", linewidths=0.8, alpha=0.5
    )
    ax.clabel(cs, inline=True, fontsize=8, fmt="%.1f")

    ax.plot(0.5, 1.0, "ko", markersize=8)
    ax.annotate(
        "baseline\n(1.0)", xy=(0.5, 1.0), xytext=(0.55, 1.3),
        fontsize=8, arrowprops=dict(arrowstyle="->", color="black"),
    )
    ax.plot(1.0, 1.0, "go", markersize=8)
    ax.annotate(
        "ceiling\n(2.0)", xy=(1.0, 1.0), xytext=(0.85, 1.4),
        fontsize=8, arrowprops=dict(arrowstyle="->", color="green"),
    )
    ax.plot(0.5, 2.0, "ro", markersize=8)
    ax.annotate(
        "floor\n(0.1)", xy=(0.5, 2.0), xytext=(0.55, 2.3),
        fontsize=8, arrowprops=dict(arrowstyle="->", color="red"),
    )

    ax.set_xlabel("autonomy_index", fontsize=11)
    ax.set_ylabel("load_ratio (cognitive_load / baseline)", fontsize=11)
    ax.set_title("Welfare Adjustment, Parameter Space", fontsize=12, pad=12)
    fig.tight_layout()

    out = out_dir / "welfare_heatmap.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Sanity checks on the paper's claims about floor, ceiling, baseline
    baseline = welfare_adjustment(np.array([0.5]), np.array([1.0]))[0]
    ceiling = welfare_adjustment(np.array([1.0]), np.array([1.0]))[0]
    floor = welfare_adjustment(np.array([0.5]), np.array([3.0]))[0]
    assert np.isclose(baseline, 1.0), f"baseline should be 1.0, got {baseline}"
    assert np.isclose(ceiling, CEILING), f"ceiling should be {CEILING}, got {ceiling}"
    assert np.isclose(floor, FLOOR), f"floor should be {FLOOR}, got {floor}"
    print(f"baseline={baseline}, ceiling={ceiling}, floor={floor}")

    plot_over_time(out_dir)
    plot_heatmap(out_dir)


if __name__ == "__main__":
    main()
