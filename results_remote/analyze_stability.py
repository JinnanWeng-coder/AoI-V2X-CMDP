"""
[RQ1-CMDP] Task-2 STABILITY analysis: 3-arm comparison at the locked base
(tau=8, eps=0.10, lam_max=20, ep=300, floor=0.0), seeds 2-7.

  A. baseline : marl_model_hard_seed{S}_t8e10           (sigma const, integral)
  B. anneal   : marl_model_hard_seed{S}_t8e10_anneal    (--sigma_anneal, integral)
  C. pid      : marl_model_hard_seed{S}_t8e10_pid       (sigma const, --dual pid)

Per-platoon violation is recomputed at the analysis tau from AoI_evolution.mat
(last-100-ep), identically to analyze_remote.metrics -> apples-to-apples.

Two stability questions, answered WITH NUMBERS:
  (a) sigma-anneal: does it pull "hair-over-eps" feasible platoons under eps?
      -> #feasible (<=eps), worst-FEASIBLE violation, #hair-over-eps platoons
         (eps < viol <= eps+0.05), per arm, mean +- 95% CI over seeds.
  (b) PID: does it kill the dual limit-cycle? -> std over the last 100 ep of
      lambda_j and of viol_rate_j (lower = stabler), over ACTIVE platoons
      (mean lambda in (0.5, lam_max-0.5), i.e. not pinned at 0 or saturated)
      and over ALL platoons; name seeds that cycled under baseline but not PID.
Cost side (power, remaining V2V demand) reported so stability isn't bought with
silently higher power/V2V. The 3 structurally-infeasible platoons are reported,
not excluded.
"""
import os
import argparse
import numpy as np
import scipy.io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze_remote import folder, _load, metrics, ci95

HERE = os.path.dirname(os.path.realpath(__file__))
OUT = HERE
EPS = 0.10
LAM_MAX = 20.0
HAIR = 0.05            # "hair-over-eps" band: eps < viol <= eps + HAIR
INFEAS = 0.5          # viol > eps + INFEAS => structurally sacrificed
ACTIVE_LO, ACTIVE_HI = 0.5, LAM_MAX - 0.5   # active-multiplier band

ARMS = [("baseline", "t8e10"), ("anneal", "t8e10_anneal"), ("pid", "t8e10_pid")]


def last100(mat):
    return mat[:, -100:] if mat is not None else None


def load_traces(seed, tag):
    """lambda.mat and viol_rate.mat last-100-ep [P,100]."""
    d = folder("hard", seed, tag)
    lam = _load(os.path.join(d, "lambda.mat"), "lambda")
    vio = _load(os.path.join(d, "viol_rate.mat"), "viol_rate")
    return (None if lam is None else lam.astype(np.float64),
            None if vio is None else vio.astype(np.float64))


def per_seed(seed, tag, tau):
    """Return a dict of per-platoon stability + feasibility stats, or None."""
    mm = metrics("hard", seed, tag, tau)        # viol@tau (last-100-ep), power, demand
    lam_full, vio_full = load_traces(seed, tag)
    if mm is None or lam_full is None or vio_full is None:
        return None
    P = mm["P"]
    viol = mm["viol"]                            # recomputed @tau from AoI_evolution
    lam100 = last100(lam_full)                   # [P,100]
    vio100 = last100(vio_full)                   # [P,100] (logged viol_rate @run tau)
    lam_mean = lam100.mean(axis=1)
    lam_std = lam100.std(axis=1, ddof=1)
    vio_std = vio100.std(axis=1, ddof=1)
    active = (lam_mean > ACTIVE_LO) & (lam_mean < ACTIVE_HI)
    feasible = viol <= EPS + 1e-9
    hair = (viol > EPS + 1e-9) & (viol <= EPS + HAIR)
    infeas = viol > EPS + INFEAS
    feas_viol = viol[feasible & ~infeas]
    return dict(
        seed=seed, P=P, viol=viol,
        n_feas=int(feasible.sum()),
        worst_feas=float(viol[~infeas].max()) if np.any(~infeas) else float("nan"),
        n_hair=int(hair.sum()),
        n_infeas=int(infeas.sum()),
        infeas_idx=[j for j in range(P) if infeas[j]],
        lam_mean=lam_mean, lam_std=lam_std, vio_std=vio_std, active=active,
        lam_std_active=float(lam_std[active].mean()) if active.any() else float("nan"),
        vio_std_active=float(vio_std[active].mean()) if active.any() else float("nan"),
        lam_std_all=float(lam_std.mean()),
        vio_std_all=float(vio_std.mean()),
        power=float(np.mean(mm["power"])),
        demand=float(np.mean(mm["demand"])),
        lam100=lam100,
    )


def agg(seeds, tag, tau):
    rows = [per_seed(s, tag, tau) for s in seeds]
    rows = [r for r in rows if r is not None]
    return rows


def fmt_ci(arr):
    arr = [a for a in arr if a is not None and not np.isnan(a)]
    if not arr:
        return "n/a"
    m, c = ci95(np.array(arr, dtype=np.float64))
    return "%.3f +- %.3f" % (m, c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=[2, 3, 4, 5, 6, 7])
    ap.add_argument("--tau", type=float, default=8.0)
    a = ap.parse_args()
    seeds, tau = a.seeds, a.tau

    arm_rows = {}
    print("\n================= TASK-2 STABILITY (tau=%g eps=%.2f) =================" % (tau, EPS))
    for name, tag in ARMS:
        rows = agg(seeds, tag, tau)
        arm_rows[name] = rows
        print("\n----- arm %s (tag %s): %d/%d seeds present -----"
              % (name, tag, len(rows), len(seeds)))
        for r in rows:
            print("  seed%d: viol=%s | feas=%d/5 worst_feas=%.3f hair=%d infeas=%d%s | "
                  "lam_std(act/all)=%.3f/%.3f vio_std(act/all)=%.3f/%.3f | pow=%.2f dem=%.0f"
                  % (r["seed"], np.round(r["viol"], 3), r["n_feas"], r["worst_feas"],
                     r["n_hair"], r["n_infeas"],
                     (" idx=%s" % r["infeas_idx"] if r["infeas_idx"] else ""),
                     r["lam_std_active"], r["lam_std_all"],
                     r["vio_std_active"], r["vio_std_all"], r["power"], r["demand"]))

    # ---- aggregate 3-arm table ----
    print("\n================= 3-ARM AGGREGATE (mean +- 95%% CI over seeds) =================")
    hdr = ["metric", "baseline", "anneal", "pid"]
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))

    def line(label, key, scale=1.0):
        cells = []
        for name, _ in ARMS:
            vals = [r[key] * scale for r in arm_rows[name]]
            cells.append(fmt_ci(vals))
        print("| %s | %s |" % (label, " | ".join(cells)))

    line("#feasible (<=eps) /5", "n_feas")
    line("worst-feasible viol", "worst_feas")
    line("#hair-over-eps platoons", "n_hair")
    line("#infeasible (sacrificed)", "n_infeas")
    line("lambda std (active pls)", "lam_std_active")
    line("lambda std (all pls)", "lam_std_all")
    line("viol_rate std (active pls)", "vio_std_active")
    line("viol_rate std (all pls)", "vio_std_all")
    line("Tx power (dBm)", "power")
    line("remaining V2V demand", "demand")

    # totals over the seed set
    print("\n  ---- totals over seed set ----")
    for name, _ in ARMS:
        rows = arm_rows[name]
        tot_feas = sum(r["n_feas"] for r in rows)
        tot_hair = sum(r["n_hair"] for r in rows)
        tot_infeas = sum(r["n_infeas"] for r in rows)
        print("  %-8s: total feasible=%d/%d  hair-over-eps=%d  sacrificed=%d"
              % (name, tot_feas, 5 * len(rows), tot_hair, tot_infeas))

    # ---- per-seed limit-cycle comparison baseline vs pid ----
    print("\n================= LIMIT-CYCLE: baseline vs PID (per seed) =================")
    base = {r["seed"]: r for r in arm_rows["baseline"]}
    pid = {r["seed"]: r for r in arm_rows["pid"]}
    print("  seed | lam_std_active base->pid | vio_std_active base->pid | cycled-under-base-not-pid?")
    cyc_seeds = []
    for s in seeds:
        if s not in base or s not in pid:
            continue
        b, p = base[s], pid[s]
        # "cycled under baseline" = active lambda std notably high; "not under pid" = lower
        lb, lp = b["lam_std_active"], p["lam_std_active"]
        cyc = (not np.isnan(lb)) and (not np.isnan(lp)) and (lb > 0.5) and (lp < 0.7 * lb)
        if cyc:
            cyc_seeds.append(s)
        print("  s%d   | %.3f -> %.3f | %.3f -> %.3f | %s"
              % (s, lb, lp, b["vio_std_active"], p["vio_std_active"], "YES" if cyc else "no"))
    print("  => seeds that cycled under baseline but not PID: %s" % (cyc_seeds or "none"))

    # ---- anneal hair-over-eps comparison ----
    print("\n================= HAIR-OVER-EPS: baseline vs anneal (per seed) =================")
    ann = {r["seed"]: r for r in arm_rows["anneal"]}
    print("  seed | worst_feas base->anneal | #hair base->anneal | #feas base->anneal")
    for s in seeds:
        if s not in base or s not in ann:
            continue
        b, n = base[s], ann[s]
        print("  s%d   | %.3f -> %.3f | %d -> %d | %d -> %d"
              % (s, b["worst_feas"], n["worst_feas"], b["n_hair"], n["n_hair"],
                 b["n_feas"], n["n_feas"]))

    make_figures(arm_rows, seeds)


def make_figures(arm_rows, seeds):
    base = {r["seed"]: r for r in arm_rows["baseline"]}
    pid = {r["seed"]: r for r in arm_rows["pid"]}
    ann = {r["seed"]: r for r in arm_rows["anneal"]}

    # Fig 1: lambda_j traces baseline vs PID, the seed with the largest baseline
    # active-lambda std (the worst limit-cycle), all platoons overlaid.
    cand = [(b["lam_std_active"], s) for s, b in base.items()
            if s in pid and not np.isnan(b["lam_std_active"])]
    if cand:
        _, s_show = max(cand)
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
        for ax, (name, store) in zip(axes, [("baseline (integral)", base), ("PID-Lagrangian", pid)]):
            r = store[s_show]
            lam100 = r["lam100"]                       # [P,100]
            for j in range(lam100.shape[0]):
                ax.plot(range(200, 300), lam100[j], label="pl%d" % j, lw=1.2)
            ax.set_title("%s  (seed %d)" % (name, s_show))
            ax.set_xlabel("episode"); ax.grid(alpha=0.3)
        axes[0].set_ylabel(r"$\lambda_j$"); axes[0].legend(fontsize=8, ncol=2)
        fig.suptitle(r"Per-platoon multiplier $\lambda_j$ over last 100 ep: baseline vs PID")
        fig.tight_layout()
        f = os.path.join(OUT, "fig_stability_lambda.png")
        fig.savefig(f, dpi=150); plt.close(fig); print("\n  saved", f)

    # Fig 2: worst-FEASIBLE violation per seed, baseline vs anneal (grouped bars),
    # with the eps line drawn.
    ss = [s for s in seeds if s in base and s in ann]
    if ss:
        bw = [base[s]["worst_feas"] for s in ss]
        aw = [ann[s]["worst_feas"] for s in ss]
        x = np.arange(len(ss)); w = 0.38
        fig, ax = plt.subplots(figsize=(1.1 * len(ss) + 2, 4))
        ax.bar(x - w / 2, bw, w, label="baseline (sigma=0.3 const)", color="#c44")
        ax.bar(x + w / 2, aw, w, label="anneal (sigma 0.3->0.05)", color="#4a4")
        ax.axhline(EPS, ls="--", color="k", lw=1, label=r"$\epsilon=%.2f$" % EPS)
        ax.set_xticks(x); ax.set_xticklabels(["s%d" % s for s in ss])
        ax.set_ylabel("worst-feasible violation"); ax.set_xlabel("seed")
        ax.set_title("Worst-feasible per-platoon violation: baseline vs sigma-anneal")
        ax.legend(fontsize=9); ax.grid(alpha=0.3, axis="y")
        fig.tight_layout()
        f = os.path.join(OUT, "fig_stability_anneal.png")
        fig.savefig(f, dpi=150); plt.close(fig); print("  saved", f)


if __name__ == "__main__":
    main()
