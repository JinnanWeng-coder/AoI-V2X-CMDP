"""
[RQ1-CMDP] soft-vs-hard analysis + figures (per-seed + rank-sorted).

The bottleneck platoon INDEX differs by seed, so a naive per-index average across
seeds mixes the worst-served platoon of one seed with a well-served platoon of
another. We therefore present:
  (a) per-seed grouped bars (soft vs hard, with the eps line)            -> fig1
  (b) a RANK-SORTED aggregate: within each seed sort platoons by SOFT
      violation (rank 0 = worst-served ... rank P-1 = best-served), then
      average each rank across seeds -> "worst platoon, 2nd worst, ..."  -> fig2
  (c) worst-served-platoon (rank 0) viol & mean AoI, soft vs hard        -> fig3
  (d) per-seed lambda_j convergence traces (hard)                        -> fig4

All last-100-ep per-platoon violation rates are recomputed at the SAME locked tau
for BOTH modes from AoI_evolution.mat (per-step AoI), so soft and hard are
compared identically.

Usage:
  python analyze.py --tau 8 --eps 0.10 --seeds 2 3 4
"""
import os
import argparse
import numpy as np
import scipy.io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.realpath(__file__))
MODEL_DIR = os.path.join(HERE, "..", "1-ModifiedMADDPGwithTDec", "model")
OUT = HERE


def rdir(mode, seed):
    return os.path.join(MODEL_DIR, "marl_model_%s_seed%d" % (mode, seed))


def load_mat(mode, seed, fname, key):
    path = os.path.join(rdir(mode, seed), fname)
    if not os.path.exists(path):
        return None
    return scipy.io.loadmat(path)[key]


def viol_last100(mode, seed, tau):
    evo = load_mat(mode, seed, "AoI_evolution.mat", "AoI_evolution")
    if evo is None:
        return None
    return np.mean(evo.astype(np.float64) > tau, axis=(1, 2))  # [P]


def aoi_last100(mode, seed):
    evo = load_mat(mode, seed, "AoI_evolution.mat", "AoI_evolution")
    if evo is None:
        return None
    return evo.astype(np.float64).mean(axis=(1, 2))  # [P]


def ci95(arr, axis=0):
    arr = np.asarray(arr, dtype=np.float64)
    n = arr.shape[axis]
    m = arr.mean(axis=axis)
    if n < 2:
        return m, np.zeros_like(m)
    sd = arr.std(axis=axis, ddof=1)
    tcrit = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}.get(n, 1.96)
    return m, tcrit * sd / np.sqrt(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tau", type=float, required=True)
    ap.add_argument("--eps", type=float, default=0.10)
    ap.add_argument("--seeds", type=int, nargs="*", default=[2, 3, 4])
    ap.add_argument("--suffix", default="", help="appended to figure/table filenames, e.g. _6seed")
    args = ap.parse_args()
    tau, eps = args.tau, args.eps
    sfx = args.suffix

    seeds = []
    data = {}  # seed -> dict(soft_v, hard_v, soft_a, hard_a)
    for s in args.seeds:
        sv = viol_last100("soft", s, tau)
        hv = viol_last100("hard", s, tau)
        if sv is None:
            continue
        data[s] = dict(soft_v=sv, hard_v=hv,
                       soft_a=aoi_last100("soft", s), hard_a=aoi_last100("hard", s))
        seeds.append(s)
    if not seeds:
        raise SystemExit("no soft runs found")
    nP = len(data[seeds[0]]["soft_v"])
    have_hard = all(data[s]["hard_v"] is not None for s in seeds)

    print("\n================ RQ1 soft-vs-hard (tau=%.1f, eps=%.2f) ================" % (tau, eps))
    print("seeds:", seeds, "| hard present:", have_hard)
    for s in seeds:
        d = data[s]
        print("\n--- seed %d ---" % s)
        print("  soft viol:", np.round(d["soft_v"], 3), " worst=%.3f@pl%d" %
              (d["soft_v"].max(), int(d["soft_v"].argmax())))
        if have_hard:
            print("  hard viol:", np.round(d["hard_v"], 3), " worst=%.3f@pl%d" %
                  (d["hard_v"].max(), int(d["hard_v"].argmax())))
        print("  soft meanAoI:", np.round(d["soft_a"], 2))
        if have_hard:
            print("  hard meanAoI:", np.round(d["hard_a"], 2))

    # ---------- per-seed pass/fail, success fraction, AoI price ----------
    passfail = {}   # seed -> dict(all_pass, n_pass, worst_hard, worst_feas_hard, soft_mAoI, hard_mAoI)
    if have_hard:
        n_all_pass = 0
        print("\n===== PER-SEED PASS/FAIL (does hard drive ALL %d platoons <= eps=%.2f?) =====" % (nP, eps))
        print("seed | #platoons<=eps | all<=eps | worst-hard | worst-FEASIBLE-hard | meanAoI soft->hard")
        for s in seeds:
            d = data[s]
            n_pass = int(np.sum(d["hard_v"] <= eps + 1e-9))
            all_pass = (n_pass == nP)
            n_all_pass += int(all_pass)
            feas = d["hard_v"][d["hard_v"] <= eps + 0.5]   # exclude clearly-unservable (~1.0)
            worst_feas = float(feas.max()) if feas.size else float("nan")
            soft_mA, hard_mA = float(d["soft_a"].mean()), float(d["hard_a"].mean())
            passfail[s] = dict(all_pass=all_pass, n_pass=n_pass, worst_hard=float(d["hard_v"].max()),
                               worst_feas_hard=worst_feas, soft_mAoI=soft_mA, hard_mAoI=hard_mA)
            print("  %d  |      %d/%d       |   %s   |   %.3f    |       %.3f          | %.2f -> %.2f (%s)" %
                  (s, n_pass, nP, "YES" if all_pass else "no ", d["hard_v"].max(), worst_feas,
                   soft_mA, hard_mA, "improve" if hard_mA < soft_mA else "WORSE"))
        print("\n>>> SUCCESS FRACTION (hard satisfies ALL %d platoons): %d/%d seeds" % (nP, n_all_pass, len(seeds)))
        wf = np.array([passfail[s]["worst_feas_hard"] for s in seeds])
        print(">>> worst-FEASIBLE-platoon hard viol across seeds: %s (mean %.3f)" %
              (np.round(wf, 3).tolist(), np.nanmean(wf)))
        n_aoi_improve = sum(passfail[s]["hard_mAoI"] < passfail[s]["soft_mAoI"] for s in seeds)
        print(">>> mean-AoI price: hard improves network mean AoI in %d/%d seeds" % (n_aoi_improve, len(seeds)))

    # ---------- rank-sorted aggregate (rank 0 = worst-served by soft) ----------
    soft_ranked, hard_ranked, soft_a_ranked, hard_a_ranked = [], [], [], []
    for s in seeds:
        d = data[s]
        order = np.argsort(-d["soft_v"])  # descending soft viol
        soft_ranked.append(d["soft_v"][order])
        soft_a_ranked.append(d["soft_a"][order])
        if have_hard:
            hard_ranked.append(d["hard_v"][order])
            hard_a_ranked.append(d["hard_a"][order])
    soft_ranked = np.stack(soft_ranked)        # [n_seed, P]
    soft_a_ranked = np.stack(soft_a_ranked)
    sr_m, sr_ci = ci95(soft_ranked)
    sa_m, sa_ci = ci95(soft_a_ranked)
    if have_hard:
        hard_ranked = np.stack(hard_ranked)
        hard_a_ranked = np.stack(hard_a_ranked)
        hr_m, hr_ci = ci95(hard_ranked)
        ha_m, ha_ci = ci95(hard_a_ranked)

    print("\n===== RANK-SORTED (rank0=worst-served by soft), mean over seeds =====")
    print("rank | soft viol        | hard viol        | soft AoI | hard AoI")
    for r in range(nP):
        hv = "%.3f+-%.3f" % (hr_m[r], hr_ci[r]) if have_hard else "-"
        ha = "%.2f" % ha_m[r] if have_hard else "-"
        print("  %d  | %.3f+-%.3f    | %-15s | %7.2f | %s" %
              (r, sr_m[r], sr_ci[r], hv, sa_m[r], ha))
    if have_hard:
        print("\nWORST-served platoon (rank0): soft viol %.3f -> hard viol %.3f" % (sr_m[0], hr_m[0]))
        print("network mean viol: soft %.3f -> hard %.3f" % (sr_m.mean(), hr_m.mean()))
        print("network mean AoI : soft %.2f -> hard %.2f" % (sa_m.mean(), ha_m.mean()))

        # ---- feasible-regime subset: platoons hard keeps <= eps + small slack ----
        # A platoon is "infeasible" if hard leaves it far above eps (lam saturates).
        SLACK = 0.05
        feas_seed_worst = []   # per-seed worst-served, only where hard satisfied it
        infeasible = []        # (seed, platoon, soft_viol, hard_viol)
        for s in seeds:
            d = data[s]
            for j in range(nP):
                if d["hard_v"][j] > eps + 0.5:   # clearly unservable (e.g. stuck ~1.0)
                    infeasible.append((s, j, d["soft_v"][j], d["hard_v"][j]))
        # feasible-regime worst-served (per seed) = max hard viol among feasible platoons
        for s in seeds:
            d = data[s]
            feas = [d["hard_v"][j] for j in range(nP) if d["hard_v"][j] <= eps + 0.5]
            feas_seed_worst.append(max(feas))
        print("\nFEASIBLE-REGIME (excluding clearly-unservable platoons):")
        print("  per-seed worst FEASIBLE-platoon hard viol:", np.round(feas_seed_worst, 3),
              " mean=%.3f" % np.mean(feas_seed_worst))
        print("  clearly-infeasible platoons (hard stuck >> eps):")
        for (s, j, sv, hv) in infeasible:
            print("    seed %d platoon %d: soft %.3f -> hard %.3f" % (s, j, sv, hv))

    rank_lbl = ["worst", "2nd", "3rd", "4th", "best"][:nP]

    # ---------------- Fig 1: per-seed grouped bars (wrap to a grid) ----------------
    ncol = min(3, len(seeds))
    nrow = int(np.ceil(len(seeds) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(5 * ncol, 4.3 * nrow), squeeze=False)
    for k, s in enumerate(seeds):
        ax = axes[k // ncol][k % ncol]
        d = data[s]
        x = np.arange(nP)
        w = 0.38
        ax.bar(x - w / 2, d["soft_v"], w, label="soft", color="#d62728", alpha=0.85)
        if have_hard:
            ax.bar(x + w / 2, d["hard_v"], w, label="hard", color="#1f77b4", alpha=0.85)
        ax.axhline(eps, ls="--", color="k", lw=1.3)
        npass = int(np.sum(d["hard_v"] <= eps + 1e-9)) if have_hard else 0
        ax.set_title("seed %d  (hard: %d/%d <= eps)" % (s, npass, nP) if have_hard else "seed %d" % s)
        ax.set_xlabel("platoon")
        ax.set_xticks(x)
        if k % ncol == 0:
            ax.set_ylabel(r"viol rate $P(\mathrm{AoI}>\tau)$")
        if k == 0:
            ax.legend()
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.3)
    for k in range(len(seeds), nrow * ncol):   # hide unused axes
        axes[k // ncol][k % ncol].axis("off")
    fig.suptitle(r"RQ1 per-platoon AoI-violation rate, soft vs hard ($\tau=%g$, $\epsilon=%.2f$, last 100 ep)" % (tau, eps))
    fig.tight_layout()
    f1 = os.path.join(OUT, "fig1_per_seed_violation%s.png" % sfx)
    fig.savefig(f1, dpi=150); plt.close(fig); print("\nsaved", f1)

    # ---------------- Fig 2: rank-sorted aggregate (mean bars + per-seed points) ----------------
    # Error bars are unreliable at rank0 due to the seed-2 infeasible outlier, so we
    # draw mean bars and OVERLAY each seed's value as a point (honest spread).
    fig, ax = plt.subplots(figsize=(8.5, 5))
    x = np.arange(nP); w = 0.38
    ax.bar(x - w / 2, sr_m, w, label="soft (reward penalty)", color="#d62728", alpha=0.7)
    if have_hard:
        ax.bar(x + w / 2, hr_m, w, label="hard (CMDP constraint)", color="#1f77b4", alpha=0.7)
    # overlay per-seed points
    for k in range(len(seeds)):
        jit = (k - (len(seeds) - 1) / 2) * 0.06
        ax.scatter(x - w / 2 + jit, soft_ranked[k], color="#7a0d0d", s=22, zorder=5)
        if have_hard:
            ax.scatter(x + w / 2 + jit, hard_ranked[k], color="#0d3a7a", s=22, zorder=5)
    ax.axhline(eps, ls="--", color="k", lw=1.5, label=r"target $\epsilon=%.2f$" % eps)
    ax.set_xticks(x); ax.set_xticklabels(rank_lbl)
    ax.set_xlabel("platoon ranked by soft violation (worst-served -> best-served)")
    ax.set_ylabel(r"violation rate $P(\mathrm{AoI}>\tau)$")
    ax.set_ylim(0, 1.05)
    ax.set_title(r"Violation by service rank ($\tau=%g$, bars=mean, dots=per-seed, %d seeds)" % (tau, len(seeds)))
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    # annotate the infeasible cases (worst-rank hard points that stay far above eps)
    if have_hard:
        n_infeas = int(np.sum(hard_ranked[:, 0] > 0.5))
        if n_infeas > 0:
            ax.annotate("%d infeasible\nplatoon(s) (->~1.0)" % n_infeas, xy=(0 + w/2, 1.0),
                        xytext=(0.7, 0.80), fontsize=8, arrowprops=dict(arrowstyle="->", color="gray"))
    fig.tight_layout()
    f2 = os.path.join(OUT, "fig2_rank_sorted_violation%s.png" % sfx)
    fig.savefig(f2, dpi=150); plt.close(fig); print("saved", f2)

    # ---------------- Fig 3: per-seed worst-served platoon viol + AoI ----------------
    if have_hard:
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
        x = np.arange(len(seeds)); w = 0.38
        sv0 = [data[s]["soft_v"][np.argmax(data[s]["soft_v"])] for s in seeds]
        hv0 = [data[s]["hard_v"][np.argmax(data[s]["soft_v"])] for s in seeds]  # same platoon as soft-worst
        sa0 = [data[s]["soft_a"][np.argmax(data[s]["soft_v"])] for s in seeds]
        ha0 = [data[s]["hard_a"][np.argmax(data[s]["soft_v"])] for s in seeds]
        axes[0].bar(x - w/2, sv0, w, label="soft", color="#d62728", alpha=0.85)
        axes[0].bar(x + w/2, hv0, w, label="hard", color="#1f77b4", alpha=0.85)
        axes[0].axhline(eps, ls="--", color="k", lw=1.5, label=r"$\epsilon=%.2f$" % eps)
        axes[0].set_xticks(x); axes[0].set_xticklabels(["seed %d" % s for s in seeds])
        axes[0].set_title("soft-worst platoon: violation rate"); axes[0].set_ylabel(r"$P(\mathrm{AoI}>\tau)$")
        axes[0].legend(); axes[0].grid(axis="y", alpha=0.3)
        axes[1].bar(x - w/2, sa0, w, label="soft", color="#d62728", alpha=0.85)
        axes[1].bar(x + w/2, ha0, w, label="hard", color="#1f77b4", alpha=0.85)
        axes[1].axhline(tau, ls=":", color="gray", lw=1.5, label=r"$\tau=%g$" % tau)
        axes[1].set_xticks(x); axes[1].set_xticklabels(["seed %d" % s for s in seeds])
        axes[1].set_title("soft-worst platoon: mean AoI"); axes[1].set_ylabel("mean AoI (slots)")
        axes[1].legend(); axes[1].grid(axis="y", alpha=0.3)
        fig.suptitle("Per-seed worst-served platoon (the platoon soft starves most), soft vs hard")
        fig.tight_layout()
        f3 = os.path.join(OUT, "fig3_worst_served_platoon%s.png" % sfx)
        fig.savefig(f3, dpi=150); plt.close(fig); print("saved", f3)

    # ---------------- Fig 4: per-seed lambda traces (wrap to a grid) ----------------
    if have_hard:
        ncol = min(3, len(seeds))
        nrow = int(np.ceil(len(seeds) / ncol))
        fig, axes = plt.subplots(nrow, ncol, figsize=(5 * ncol, 4.0 * nrow), squeeze=False)
        for k, s in enumerate(seeds):
            ax = axes[k // ncol][k % ncol]
            lam = load_mat("hard", s, "lambda.mat", "lambda")
            if lam is not None:
                for j in range(lam.shape[0]):
                    ax.plot(lam[j], lw=1.5, label=r"$\lambda_{%d}$" % j)
            ax.set_title("seed %d" % s); ax.set_xlabel("episode")
            if k % ncol == 0:
                ax.set_ylabel(r"$\lambda_j$")
            ax.legend(ncol=2, fontsize=8); ax.grid(alpha=0.3)
        for k in range(len(seeds), nrow * ncol):
            axes[k // ncol][k % ncol].axis("off")
        fig.suptitle("Per-platoon multiplier convergence (hard)")
        fig.tight_layout()
        f4 = os.path.join(OUT, "fig4_lambda_convergence%s.png" % sfx)
        fig.savefig(f4, dpi=150); plt.close(fig); print("saved", f4)

    # ---------------- summary table ----------------
    tbl = os.path.join(OUT, "summary_table%s.md" % sfx)
    with open(tbl, "w") as f:
        f.write("# RQ1 soft-vs-hard summary (tau=%g, eps=%.2f, seeds %s)\n\n" % (tau, eps, seeds))
        if have_hard:
            n_all_pass = sum(passfail[s]["all_pass"] for s in seeds)
            n_aoi_improve = sum(passfail[s]["hard_mAoI"] < passfail[s]["soft_mAoI"] for s in seeds)
            f.write("## Pass/fail and success fraction\n\n")
            f.write("**SUCCESS FRACTION (hard satisfies ALL %d platoons <= eps): %d/%d seeds.** "
                    "Mean-AoI improves under hard in %d/%d seeds.\n\n" %
                    (nP, n_all_pass, len(seeds), n_aoi_improve, len(seeds)))
            f.write("| seed | #platoons<=eps | all<=eps | worst-hard viol | worst-FEASIBLE-hard | meanAoI soft->hard |\n")
            f.write("|---|---|---|---|---|---|\n")
            for s in seeds:
                pf = passfail[s]
                f.write("| %d | %d/%d | %s | %.3f | %.3f | %.2f -> %.2f (%s) |\n" %
                        (s, pf["n_pass"], nP, "YES" if pf["all_pass"] else "no",
                         pf["worst_hard"], pf["worst_feas_hard"], pf["soft_mAoI"], pf["hard_mAoI"],
                         "improve" if pf["hard_mAoI"] < pf["soft_mAoI"] else "WORSE"))
            wf = np.array([passfail[s]["worst_feas_hard"] for s in seeds])
            f.write("\nworst-FEASIBLE-platoon hard viol per seed: %s (mean %.3f) -- "
                    "where it is ~eps, hard drove the binding platoon to the boundary.\n\n" %
                    (np.round(wf, 3).tolist(), np.nanmean(wf)))
        f.write("## Per-seed (last-100-ep viol recomputed @tau)\n\n")
        for s in seeds:
            d = data[s]
            f.write("**seed %d** soft viol %s (worst %.3f@pl%d); " %
                    (s, np.round(d["soft_v"], 3).tolist(), d["soft_v"].max(), int(d["soft_v"].argmax())))
            if have_hard:
                f.write("hard viol %s (worst %.3f@pl%d)" %
                        (np.round(d["hard_v"], 3).tolist(), d["hard_v"].max(), int(d["hard_v"].argmax())))
            f.write("\n\n")
        f.write("## Rank-sorted (rank0 = worst-served by soft), mean +/- 95%%CI over seeds\n\n")
        f.write("| rank | soft viol | hard viol | soft meanAoI | hard meanAoI |\n|---|---|---|---|---|\n")
        for r in range(nP):
            hv = "%.3f +/- %.3f" % (hr_m[r], hr_ci[r]) if have_hard else "-"
            ha = "%.2f" % ha_m[r] if have_hard else "-"
            f.write("| %s | %.3f +/- %.3f | %s | %.2f | %s |\n" %
                    (rank_lbl[r], sr_m[r], sr_ci[r], hv, sa_m[r], ha))
        if have_hard:
            f.write("\nnetwork mean viol: soft %.3f -> hard %.3f; "
                    "network mean AoI: soft %.2f -> hard %.2f\n" %
                    (sr_m.mean(), hr_m.mean(), sa_m.mean(), ha_m.mean()))
    print("saved", tbl)


if __name__ == "__main__":
    main()
