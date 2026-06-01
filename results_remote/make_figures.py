"""
[RQ1-CMDP] Generate the report figures from the completed runs.
Depends on analyze_remote.py (same folder) for the metric loaders.

Figures produced (results_remote/):
  fig_softsweep.png          per-seed worst-platoon viol vs tau (soft, tau-independent policy)
  fig_phase_diagram.png      heatmap: mean #platoons <= eps over (tau, eps)   [also via analyze_remote phase]
  fig_headline_violation.png per-seed grouped bars soft vs hard @ t8e10, eps line
  fig_cost_tradeoff.png      network mean power / V2V rate / V2I success, soft vs hard (mean+95CI)
  fig_lambda.png             per-seed lambda_j traces @ t8e10
  fig_floor.png              Exp2: seed-2 (and 3,4) worst platoon viol & AoI, no-floor vs floor

Usage: python make_figures.py --seeds 2 3 4 5 6 7 --grid_seeds 2 3 4
"""
import os
import argparse
import numpy as np
import scipy.io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import analyze_remote as A

OUT = A.HERE
EPS = 0.10
TAU = 8.0


def _save(fig, name):
    f = os.path.join(OUT, name)
    fig.savefig(f, dpi=150)
    plt.close(fig)
    print("saved", f)


def fig_softsweep(seeds, taus=(6, 8, 10, 12)):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    any_data = False
    worst_by_tau = {t: [] for t in taus}
    for s in seeds:
        d = A.folder("soft", s, "base")
        evo = A._load(os.path.join(d, "AoI_evolution.mat"), "AoI_evolution")
        if evo is None:
            continue
        any_data = True
        evo = evo.astype(np.float64)
        ys = [np.mean(evo > t, axis=(1, 2)).max() for t in taus]
        for t, y in zip(taus, ys):
            worst_by_tau[t].append(y)
        ax.plot(taus, ys, marker="o", alpha=0.55, lw=1.2, label="seed %d" % s)
    if any_data:
        mean = [np.mean(worst_by_tau[t]) for t in taus]
        ax.plot(taus, mean, marker="s", color="k", lw=2.6, label="mean")
    ax.axhline(EPS, ls="--", color="gray", label=r"$\epsilon=0.10$")
    ax.set_xlabel(r"AoI threshold $\tau$ (slots)")
    ax.set_ylabel(r"worst-platoon $P(\mathrm{AoI}>\tau)$ (soft)")
    ax.set_title("SOFT baseline: worst-platoon violation vs $\\tau$ (binding for all $\\tau\\leq12$)")
    ax.invert_xaxis()
    ax.legend(fontsize=8, ncol=2); ax.grid(alpha=0.3)
    _save(fig, "fig_softsweep.png")


def fig_headline(seeds, tau=TAU, eps=EPS, hard_tag="t8e10"):
    seeds = [s for s in seeds
             if A.metrics("soft", s, "base", tau) and A.metrics("hard", s, hard_tag, tau)]
    if not seeds:
        print("fig_headline: no paired data"); return
    ncol = min(3, len(seeds)); nrow = int(np.ceil(len(seeds) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.7 * ncol, 3.9 * nrow), squeeze=False)
    for k, s in enumerate(seeds):
        ax = axes[k // ncol][k % ncol]
        ms = A.metrics("soft", s, "base", tau); mh = A.metrics("hard", s, hard_tag, tau)
        P = ms["P"]; x = np.arange(P); w = 0.38
        ax.bar(x - w/2, ms["viol"], w, label="soft", color="#d62728", alpha=0.85)
        ax.bar(x + w/2, mh["viol"], w, label="hard", color="#1f77b4", alpha=0.85)
        ax.axhline(eps, ls="--", color="k", lw=1.2)
        npass = int(np.sum(mh["viol"] <= eps + 1e-9))
        ax.set_title("seed %d  (hard %d/%d $\\leq\\epsilon$)" % (s, npass, P))
        ax.set_xlabel("platoon"); ax.set_xticks(x); ax.set_ylim(0, 1.05)
        if k % ncol == 0: ax.set_ylabel(r"$P(\mathrm{AoI}>\tau)$")
        if k == 0: ax.legend()
        ax.grid(axis="y", alpha=0.3)
    for k in range(len(seeds), nrow*ncol): axes[k//ncol][k%ncol].axis("off")
    fig.suptitle(r"RQ1 per-platoon violation rate, soft vs hard ($\tau=%g,\ \epsilon=%.2f$, last 100 ep)" % (tau, eps))
    fig.tight_layout(); _save(fig, "fig_headline_violation.png")


def fig_cost(seeds, tau=TAU, hard_tag="t8e10"):
    keys = [("power", "Tx power (dBm)"), ("v2v", "V2V rate"), ("v2i_succ", "V2I success frac")]
    soft = {k: [] for k, _ in keys}; hard = {k: [] for k, _ in keys}
    for s in seeds:
        ms = A.metrics("soft", s, "base", tau); mh = A.metrics("hard", s, hard_tag, tau)
        if ms is None or mh is None: continue
        for k, _ in keys:
            if ms[k] is not None: soft[k].append(np.mean(ms[k]))
            if mh[k] is not None: hard[k].append(np.mean(mh[k]))
    fig, axes = plt.subplots(1, len(keys), figsize=(4.2*len(keys), 4))
    for ax, (k, lbl) in zip(axes, keys):
        sm, sci = A.ci95(soft[k]) if soft[k] else (0, 0)
        hm, hci = A.ci95(hard[k]) if hard[k] else (0, 0)
        ax.bar([0, 1], [sm, hm], yerr=[sci, hci], capsize=5,
               color=["#d62728", "#1f77b4"], alpha=0.85)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["soft", "hard"])
        ax.set_title(lbl); ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Cost side of the AoI guarantee (network mean $\\pm$ 95%% CI, %d seeds)" % len(seeds))
    fig.tight_layout(); _save(fig, "fig_cost_tradeoff.png")


def fig_lambda(seeds, hard_tag="t8e10"):
    seeds = [s for s in seeds if os.path.exists(os.path.join(A.folder("hard", s, hard_tag), "lambda.mat"))]
    if not seeds:
        print("fig_lambda: no data"); return
    ncol = min(3, len(seeds)); nrow = int(np.ceil(len(seeds)/ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.7*ncol, 3.6*nrow), squeeze=False)
    for k, s in enumerate(seeds):
        ax = axes[k//ncol][k%ncol]
        lam = scipy.io.loadmat(os.path.join(A.folder("hard", s, hard_tag), "lambda.mat"))["lambda"]
        for j in range(lam.shape[0]):
            ax.plot(lam[j], lw=1.4, label=r"$\lambda_%d$" % j)
        ax.set_title("seed %d" % s); ax.set_xlabel("episode")
        if k % ncol == 0: ax.set_ylabel(r"$\lambda_j$")
        ax.legend(ncol=2, fontsize=7); ax.grid(alpha=0.3)
    for k in range(len(seeds), nrow*ncol): axes[k//ncol][k%ncol].axis("off")
    fig.suptitle("Per-platoon multiplier convergence (hard, $\\tau=8,\\epsilon=0.10$)")
    fig.tight_layout(); _save(fig, "fig_lambda.png")


def fig_floor(seeds, tau=TAU, eps=EPS, base_tag="t8e10"):
    floor_tag = base_tag + "_floor"
    rows = []
    for s in seeds:
        mn = A.metrics("hard", s, base_tag, tau); mf = A.metrics("hard", s, floor_tag, tau)
        if mn is None or mf is None: continue
        j = int(mn["viol"].argmax())   # worst platoon under no-floor
        rows.append((s, j, mn["viol"][j], mf["viol"][j], mn["aoi"][j], mf["aoi"][j]))
    if not rows:
        print("fig_floor: no data"); return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    x = np.arange(len(rows)); w = 0.38
    axes[0].bar(x - w/2, [r[2] for r in rows], w, label="no floor", color="#1f77b4", alpha=0.85)
    axes[0].bar(x + w/2, [r[3] for r in rows], w, label="floor 0.005", color="#2ca02c", alpha=0.85)
    axes[0].axhline(eps, ls="--", color="k", lw=1.2, label=r"$\epsilon$")
    axes[0].set_title("worst platoon: violation"); axes[0].set_ylabel(r"$P(\mathrm{AoI}>\tau)$")
    axes[1].bar(x - w/2, [r[4] for r in rows], w, label="no floor", color="#1f77b4", alpha=0.85)
    axes[1].bar(x + w/2, [r[5] for r in rows], w, label="floor 0.005", color="#2ca02c", alpha=0.85)
    axes[1].set_title("worst platoon: mean AoI"); axes[1].set_ylabel("mean AoI (slots)")
    for ax in axes:
        ax.set_xticks(x); ax.set_xticklabels(["seed %d\n(pl%d)" % (r[0], r[1]) for r in rows])
        ax.legend(); ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Exp2 feasibility safeguard: AoI-penalty floor vs original hard mode")
    fig.tight_layout(); _save(fig, "fig_floor.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=[2, 3, 4, 5, 6, 7])
    ap.add_argument("--grid_seeds", type=int, nargs="*", default=[2, 3, 4])
    a = ap.parse_args()
    fig_softsweep(a.seeds)
    fig_headline(a.seeds)
    fig_cost(a.seeds)
    fig_lambda(a.seeds)
    fig_floor(a.grid_seeds)


if __name__ == "__main__":
    main()
