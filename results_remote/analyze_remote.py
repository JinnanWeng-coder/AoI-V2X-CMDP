"""
[RQ1-CMDP] Remote analysis: multi-metric soft-vs-hard, tau/eps phase diagram,
and the feasibility-safeguard (aoi_floor) before/after.

All per-platoon, last-100-episode statistics are recomputed from the per-step
[P,100,T] .mat tensors (AoI_evolution / V2I / V2V / power / demand), so soft and
hard are compared identically at the SAME analysis tau. We report MORE than AoI:
the cost side (transmit power, V2V rate, remaining V2V demand, V2I rate, V2I
success) is shown alongside the AoI-violation guarantee.

Folder convention (model/):
  soft  : marl_model_soft_seed{S}_base          (soft is tau-independent)
  hard  : marl_model_hard_seed{S}_t{T}e{E}      (E = eps*100, e.g. t8e10)
  floor : marl_model_hard_seed{S}_t8e10_floor   (Exp2 safeguard)

Usage examples:
  python analyze_remote.py softsweep --seeds 2 3 4 5 6 7
  python analyze_remote.py phase     --seeds 2 3 4 --taus 8 10 12 --epses 0.10 0.15
  python analyze_remote.py metrics   --seeds 2 3 4 5 6 7 --tau 8 --eps 0.10
  python analyze_remote.py floor     --seeds 2 3 4 --tau 8 --eps 0.10
  python analyze_remote.py all       --seeds 2 3 4 5 6 7
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
V2I_MIN = 540.0   # minimum V2I rate (3 bps/Hz * B.W * time_fast) -> "success" if >=

T_CRIT = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447, 8: 2.365}


def folder(mode, seed, tag):
    return os.path.join(MODEL_DIR, "marl_model_%s_seed%d_%s" % (mode, seed, tag))


def _load(path, key):
    if not os.path.exists(path):
        return None
    return scipy.io.loadmat(path)[key]


def metrics(mode, seed, tag, tau):
    """Per-platoon last-100-ep metrics from a run folder. Returns dict of [P] arrays."""
    d = folder(mode, seed, tag)
    evo = _load(os.path.join(d, "AoI_evolution.mat"), "AoI_evolution")
    if evo is None:
        return None
    evo = evo.astype(np.float64)                       # [P,100,T]
    v2i = _load(os.path.join(d, "V2I.mat"), "V2I")
    v2v = _load(os.path.join(d, "V2V.mat"), "V2V")
    pwr = _load(os.path.join(d, "power.mat"), "power")
    dem = _load(os.path.join(d, "demand.mat"), "demand")
    lam = _load(os.path.join(d, "lambda.mat"), "lambda")     # [P,n_ep]
    P = evo.shape[0]

    def m(x):
        return None if x is None else x.astype(np.float64).mean(axis=(1, 2))  # [P]

    out = dict(
        viol=np.mean(evo > tau, axis=(1, 2)),
        aoi=evo.mean(axis=(1, 2)),
        v2i=m(v2i),
        v2i_succ=(None if v2i is None else np.mean(v2i.astype(np.float64) >= V2I_MIN, axis=(1, 2))),
        power=m(pwr),
        v2v=m(v2v),
        demand=m(dem),
        lam_final=(None if lam is None else lam.astype(np.float64)[:, -100:].mean(axis=1)),
        P=P,
    )
    return out


def ci95(arr, axis=0):
    arr = np.asarray(arr, dtype=np.float64)
    n = arr.shape[axis]
    mean = arr.mean(axis=axis)
    if n < 2:
        return mean, np.zeros_like(mean)
    sd = arr.std(axis=axis, ddof=1)
    return mean, T_CRIT.get(n, 1.96) * sd / np.sqrt(n)


# --------------------------------------------------------------------------- #
# (1) soft tau-sweep  (soft policy is tau-independent -> recompute, no training)
# --------------------------------------------------------------------------- #
def task_softsweep(seeds, taus, **_):
    print("\n===== SOFT tau-sweep (per-platoon P(AoI>tau), last-100-ep) =====")
    rows = []
    per_seed_worst = {t: [] for t in taus}
    for s in seeds:
        d = folder("soft", s, "base")
        evo = _load(os.path.join(d, "AoI_evolution.mat"), "AoI_evolution")
        if evo is None:
            print("  seed %d: MISSING (%s)" % (s, d)); continue
        evo = evo.astype(np.float64)
        print("\n  seed %d:" % s)
        for t in taus:
            v = np.mean(evo > t, axis=(1, 2))
            per_seed_worst[t].append(v.max())
            print("    tau=%2g: viol=%s  worst=%.3f@pl%d" %
                  (t, np.round(v, 3), v.max(), int(v.argmax())))
            rows.append((s, t, v))
    print("\n  mean WORST-platoon viol vs tau (over %d seeds):" % len(seeds))
    for t in taus:
        if per_seed_worst[t]:
            arr = np.array(per_seed_worst[t])
            print("    tau=%2g: mean worst=%.3f  (per-seed %s)" %
                  (t, arr.mean(), np.round(arr, 3).tolist()))
    return rows


# --------------------------------------------------------------------------- #
# (2) tau/eps phase diagram (HARD): how many platoons driven <= eps, per seed
# --------------------------------------------------------------------------- #
def task_phase(seeds, taus, epses, **_):
    print("\n===== HARD tau/eps PHASE DIAGRAM (#platoons <= eps, last-100-ep @run tau) =====")
    grid = {}   # (tau,eps) -> list over seeds of (n_pass, P, worst_feas, infeas_list)
    for t in taus:
        for e in epses:
            tag = "t%de%d" % (int(t), int(round(e * 100)))
            cell = []
            for s in seeds:
                mm = metrics("hard", s, tag, t)
                if mm is None:
                    continue
                P = mm["P"]
                viol = mm["viol"]
                n_pass = int(np.sum(viol <= e + 1e-9))
                feas = viol[viol <= e + 0.5]
                worst_feas = float(feas.max()) if feas.size else float("nan")
                infeas = [(s, j, float(viol[j])) for j in range(P) if viol[j] > e + 0.5]
                cell.append(dict(seed=s, n_pass=n_pass, P=P, worst_feas=worst_feas,
                                 infeas=infeas, viol=viol))
            grid[(t, e)] = cell
    # per-seed detail (kept for traceability)
    print("\n  (tau, eps) | per-seed #pass/P | strict-all-pass seeds | worst-feasible (mean) | infeasible (seed,pl)")
    for (t, e), cell in grid.items():
        if not cell:
            print("  (%g,%.2f): no data" % (t, e)); continue
        passes = ["%d/%d" % (c["n_pass"], c["P"]) for c in cell]
        n_all = sum(c["n_pass"] == c["P"] for c in cell)
        wf = np.array([c["worst_feas"] for c in cell])
        infeas = [iv for c in cell for iv in c["infeas"]]
        print("  (%g,%.2f) | %s | %d/%d strict | %.3f (%s) | %s" %
              (t, e, " ".join(passes), n_all, len(cell), np.nanmean(wf),
               np.round(wf, 3).tolist(),
               ["s%dpl%d=%.2f" % (s, j, v) for (s, j, v) in infeas] or "none"))

    # aggregate markdown table: per cell, mean +- 95% CI over the seeds in that cell
    print("\n  --- 6-seed aggregate (mean +- 95%% CI, t_crit) ---")
    print("\n| (tau, eps) | seeds | mean #pass/5 (+-95CI) | strict 5/5 | worst-feasible viol (mean+-95CI) | #infeasible (sacrificed) |")
    print("|---|---|---|---|---|---|")
    for (t, e), cell in grid.items():
        if not cell:
            print("| (%g, %.2f) | 0 | - | - | - | - |" % (t, e)); continue
        n = len(cell)
        npass = np.array([c["n_pass"] for c in cell], dtype=np.float64)
        wf = np.array([c["worst_feas"] for c in cell], dtype=np.float64)
        pm, pci = ci95(npass)
        # worst-feasible CI over seeds that HAVE a feasible platoon (nan-safe)
        wf_ok = wf[~np.isnan(wf)]
        wm, wci = ci95(wf_ok) if wf_ok.size else (float("nan"), 0.0)
        n_all = sum(c["n_pass"] == c["P"] for c in cell)
        n_infeas = sum(len(c["infeas"]) for c in cell)        # sacrificed (seed,platoon) pairs
        seeds_infeas = sum(1 for c in cell if c["infeas"])    # seeds with >=1 sacrificed
        print("| (%g, %.2f) | %d | %.2f +- %.2f | %d/%d | %.3f +- %.3f | %d (in %d/%d seeds) |" %
              (t, e, n, pm, pci, n_all, n, wm, wci, n_infeas, seeds_infeas, n))
    _plot_phase(grid, seeds, taus, epses)
    return grid


def _plot_phase(grid, seeds, taus, epses):
    # heatmap: rows=tau, cols=eps, value=mean #platoons satisfied across seeds
    fig, ax = plt.subplots(figsize=(1.6 * len(epses) + 2, 1.1 * len(taus) + 2))
    M = np.full((len(taus), len(epses)), np.nan)
    for i, t in enumerate(taus):
        for k, e in enumerate(epses):
            cell = grid.get((t, e), [])
            if cell:
                M[i, k] = np.mean([c["n_pass"] for c in cell])
    im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=5, aspect="auto")
    ax.set_xticks(range(len(epses))); ax.set_xticklabels(["%.2f" % e for e in epses])
    ax.set_yticks(range(len(taus))); ax.set_yticklabels(["%g" % t for t in taus])
    ax.set_xlabel(r"target violation $\epsilon$"); ax.set_ylabel(r"AoI threshold $\tau$ (slots)")
    for i in range(len(taus)):
        for k in range(len(epses)):
            if not np.isnan(M[i, k]):
                ax.text(k, i, "%.1f" % M[i, k], ha="center", va="center", fontsize=11)
    ax.set_title("HARD: mean #platoons (of 5) driven $\\leq\\epsilon$\n(green=all 5 feasible, %d seeds)" % len(seeds))
    fig.colorbar(im, ax=ax, label="#platoons satisfied")
    fig.tight_layout()
    f = os.path.join(OUT, "fig_phase_diagram.png")
    fig.savefig(f, dpi=150); plt.close(fig); print("\n  saved", f)


# --------------------------------------------------------------------------- #
# (3) multi-metric soft-vs-hard table with CIs (locked tau/eps)
# --------------------------------------------------------------------------- #
def task_metrics(seeds, tau, eps, hard_tag=None, **_):
    hard_tag = hard_tag or ("t%de%d" % (int(tau), int(round(eps * 100))))
    print("\n===== MULTI-METRIC soft vs hard (tau=%g, eps=%.2f, hard tag=%s) =====" % (tau, eps, hard_tag))
    keys = ["viol", "aoi", "power", "v2v", "demand", "v2i", "v2i_succ"]
    nice = {"viol": "viol P(AoI>tau)", "aoi": "mean AoI (slots)", "power": "Tx power (dBm)",
            "v2v": "V2V rate", "demand": "remaining V2V demand", "v2i": "V2I rate",
            "v2i_succ": "V2I success (>=%d)" % int(V2I_MIN)}
    # collect network means per seed
    net = {"soft": {k: [] for k in keys}, "hard": {k: [] for k in keys}}
    used = []
    for s in seeds:
        ms = metrics("soft", s, "base", tau)
        mh = metrics("hard", s, hard_tag, tau)
        if ms is None or mh is None:
            print("  seed %d: missing (soft=%s hard=%s)" % (s, ms is not None, mh is not None)); continue
        used.append(s)
        for k in keys:
            if ms[k] is not None:
                net["soft"][k].append(np.mean(ms[k]))
            if mh[k] is not None:
                net["hard"][k].append(np.mean(mh[k]))
    print("  seeds used:", used)
    print("\n  | metric | soft (mean+-95CI) | hard (mean+-95CI) |")
    print("  |---|---|---|")
    table = {}
    for k in keys:
        sm, sci = ci95(net["soft"][k]) if net["soft"][k] else (float("nan"), 0)
        hm, hci = ci95(net["hard"][k]) if net["hard"][k] else (float("nan"), 0)
        table[k] = (sm, sci, hm, hci)
        print("  | %s | %.3f +- %.3f | %.3f +- %.3f |" % (nice[k], sm, sci, hm, hci))
    return table, used


# --------------------------------------------------------------------------- #
# (4) feasibility safeguard (Exp2): floor vs no-floor on seed2 (+3,4)
# --------------------------------------------------------------------------- #
def task_floor(seeds, tau, eps, **_):
    base_tag = "t%de%d" % (int(tau), int(round(eps * 100)))
    floor_tag = base_tag + "_floor"
    print("\n===== Exp2 feasibility safeguard (no-floor=%s vs floor=%s) =====" % (base_tag, floor_tag))
    print("  per-platoon viol@tau=%g (NO-floor -> FLOOR), mean AoI, power:" % tau)
    for s in seeds:
        mn = metrics("hard", s, base_tag, tau)
        mf = metrics("hard", s, floor_tag, tau)
        print("\n  -- seed %d --" % s)
        if mn is None:
            print("    no-floor MISSING");
        if mf is None:
            print("    floor MISSING")
        if mn is None or mf is None:
            continue
        for j in range(mn["P"]):
            print("    pl%d: viol %.3f -> %.3f | AoI %.2f -> %.2f | pow %.2f -> %.2f" %
                  (j, mn["viol"][j], mf["viol"][j], mn["aoi"][j], mf["aoi"][j],
                   mn["power"][j], mf["power"][j]))
        print("    NET: viol %.3f->%.3f  AoI %.2f->%.2f  worst-viol %.3f->%.3f" %
              (mn["viol"].mean(), mf["viol"].mean(), mn["aoi"].mean(), mf["aoi"].mean(),
               mn["viol"].max(), mf["viol"].max()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task", choices=["softsweep", "phase", "metrics", "floor", "all"])
    ap.add_argument("--seeds", type=int, nargs="*", default=[2, 3, 4])
    ap.add_argument("--taus", type=float, nargs="*", default=[8, 10, 12])
    ap.add_argument("--epses", type=float, nargs="*", default=[0.10, 0.15])
    ap.add_argument("--tau", type=float, default=8.0)
    ap.add_argument("--eps", type=float, default=0.10)
    ap.add_argument("--hard_tag", default=None)
    a = ap.parse_args()
    kw = dict(seeds=a.seeds, taus=a.taus, epses=a.epses, tau=a.tau, eps=a.eps, hard_tag=a.hard_tag)
    if a.task in ("softsweep", "all"):
        task_softsweep(**kw)
    if a.task in ("phase", "all"):
        task_phase(**kw)
    if a.task in ("metrics", "all"):
        task_metrics(**kw)
    if a.task in ("floor", "all"):
        task_floor(**kw)


if __name__ == "__main__":
    main()
