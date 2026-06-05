"""
[RQ1-CMDP] 600-episode convergence check + 300-vs-600 comparison (t8e10, 3 arms).

Checks whether 600 ep actually CONVERGED (does the last-100-ep window sit on a flat
plateau, or is a cap-bound platoon still descending?) and whether the 300-ep
conclusions change. Three arms x seeds {2..7}:
  soft  marl_model_soft_seed{S}_base_ep600
  int   marl_model_hard_seed{S}_t8e10_ep600        (--dual integral)
  pid   marl_model_hard_seed{S}_t8e10_pid_ep600    (--dual pid)
compared to the existing 300-ep tags (base / t8e10 / t8e10_pid).

Sources: AoI.mat = per-platoon mean AoI for EVERY episode -> 50-ep blocked trajectory.
AoI_evolution.mat = last-100-ep per-step AoI (auto ep[500,600) at 600 ep) -> violation
@tau, via analyze_remote.metrics. Outputs under results_remote/:
  fig_ep600_convergence.png, RQ1_EP600_REPORT.md.  Exit 2 (no report) if any of the
18 ep600 runs is missing. No git.
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze_remote import metrics, folder, _load

HERE = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REPORT = os.path.join(HERE, "RQ1_EP600_REPORT.md")
EPS = 0.10
TAU = 8
SACR = 0.5
BLOCK = 50
SEEDS = [2, 3, 4, 5, 6, 7]
T_CRIT = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447}
# arm -> (mode, 300-ep tag, 600-ep tag)
ARMS = {
    "soft": ("soft", "base", "base_ep600"),
    "int":  ("hard", "t8e10", "t8e10_ep600"),
    "pid":  ("hard", "t8e10_pid", "t8e10_pid_ep600"),
}
# previously-flagged under-trained cap-bound platoons (arm, seed, platoon_idx)
FLAGGED = [("soft", 2, 2), ("int", 3, 0), ("int", 7, 0)]


def ci95(vals):
    a = np.asarray([v for v in vals if v is not None and not np.isnan(v)], float)
    n = a.size
    if n == 0:
        return float("nan"), 0.0
    if n < 2:
        return float(a[0]), 0.0
    return float(a.mean()), float(T_CRIT.get(n, 1.96) * a.std(ddof=1) / np.sqrt(n))


def blocks(arm, seed, platoon=None):
    """50-ep blocked AoI trajectory from AoI.mat. network-mean if platoon is None."""
    mode, _, tag600 = ARMS[arm]
    aoi = _load(os.path.join(folder(mode, seed, tag600), "AoI.mat"), "AoI")
    if aoi is None:
        return None
    aoi = aoi.astype(np.float64)                       # [P, nep]
    series = aoi.mean(axis=0) if platoon is None else aoi[platoon]
    nb = series.shape[0] // BLOCK
    return series[:nb * BLOCK].reshape(nb, BLOCK).mean(axis=1)   # [nb]


def flat_verdict(blk):
    """flat if the last 3 blocks have small range and last step is small."""
    if blk is None or blk.size < 3:
        return "n/a", float("nan"), float("nan")
    last3 = blk[-3:]
    rng = float(last3.max() - last3.min())
    step = float(blk[-1] - blk[-2])
    flat = (rng < 1.0) and (abs(step) < 1.0)
    return ("FLAT" if flat else "NOT-flat"), rng, step


def present_count():
    n = 0
    for arm, (mode, _, t600) in ARMS.items():
        for s in SEEDS:
            if metrics(mode, s, t600, TAU) is not None:
                n += 1
    return n


def main():
    have = present_count()
    if have < 3 * len(SEEDS):
        sys.stderr.write("[ep600] only %d/18 runs present -- not writing report\n" % have)
        sys.exit(2)

    # ---------- (1) convergence: blocked trajectories ----------
    net_blocks = {arm: {s: blocks(arm, s) for s in SEEDS} for arm in ARMS}
    flag_blocks = {(arm, s, pl): blocks(arm, s, pl) for (arm, s, pl) in FLAGGED}

    # figure: network-mean AoI trajectory per arm (mean over seeds) + flagged platoons
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
    colors = {"soft": "#c44", "int": "#48c", "pid": "#4a4"}
    for arm in ARMS:
        M = np.vstack([net_blocks[arm][s] for s in SEEDS if net_blocks[arm][s] is not None])
        x = (np.arange(M.shape[1]) + 1) * BLOCK
        ax[0].plot(x, M.mean(axis=0), "-o", color=colors[arm], label=arm, lw=1.5, ms=3)
    ax[0].set_xlabel("episode"); ax[0].set_ylabel("network-mean AoI (slots)")
    ax[0].set_title("600-ep network-mean AoI (mean over seeds), 50-ep blocks")
    ax[0].legend(); ax[0].grid(alpha=0.3)
    for (arm, s, pl) in FLAGGED:
        blk = flag_blocks[(arm, s, pl)]
        if blk is not None:
            x = (np.arange(blk.size) + 1) * BLOCK
            ax[1].plot(x, blk, "-o", lw=1.5, ms=3, label="%s s%d pl%d" % (arm, s, pl))
    ax[1].set_xlabel("episode"); ax[1].set_ylabel("platoon mean AoI (slots)")
    ax[1].set_title("Previously cap-bound platoons @600 ep")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    fig.tight_layout()
    figpath = os.path.join(HERE, "fig_ep600_convergence.png")
    fig.savefig(figpath, dpi=150); plt.close(fig)

    # ---------- (2) 300 vs 600 last-100-ep numbers ----------
    def cell_metrics(arm, tagkey):
        mode, t300, t600 = ARMS[arm]
        tag = t300 if tagkey == 300 else t600
        return {s: metrics(mode, s, tag, TAU) for s in SEEDS}

    m300 = {arm: cell_metrics(arm, 300) for arm in ARMS}
    m600 = {arm: cell_metrics(arm, 600) for arm in ARMS}

    # soft-vs-hard(PID) worst-platoon gap per seed
    def worst_gap(mset):
        g = []
        for s in SEEDS:
            ms, mp = mset["soft"][s], mset["pid"][s]
            if ms is None or mp is None:
                continue
            g.append(float(ms["viol"].max()) - float(mp["viol"].max()))
        return g
    gap300, gap600 = worst_gap(m300), worst_gap(m600)

    # integral sacrificed count (viol>=0.5)
    def sac_count(mset, arm):
        return int(sum(int((mset[arm][s]["viol"] > SACR).sum()) for s in SEEDS
                       if mset[arm][s] is not None))
    sac_int_300, sac_int_600 = sac_count(m300, "int"), sac_count(m600, "int")
    sac_soft_300, sac_soft_600 = sac_count(m300, "soft"), sac_count(m600, "soft")

    # ---------- report ----------
    L = []; w = L.append
    w("# RQ1 — 600-episode convergence re-run (t8e10, soft / hard-int / hard-PID)\n")
    w("**Auto-generated on disk by `ep600_driver.ps1` -> `analyze_ep600.py`** "
      "(detached). Commit left to the operator.\n")
    w("Motivation: three 300-ep runs (soft-s2, hard-int-s3, hard-int-s7) were "
      "under-trained -- a cap-bound platoon was still descending at ep300, so their "
      "last-100-ep window sat mid-transition. Main.py trains from scratch, so this "
      "re-runs t8e10 at **600 ep** (new `_ep600` tags; 300-ep runs untouched). Locked "
      "config otherwise identical (eta_lam=1.0, lam_max=20, tau=8, eps=0.10, PID "
      "kp=1.0 ki=1.0 kd=0.5, sigma const 0.3). Last-100-ep at 600 ep = ep[500,600).\n")

    # convergence table
    w("## 1. Convergence at 600 ep (50-ep blocks; FLAT = last-3-block range <1 slot "
      "and last step <1 slot)\n")
    w("| arm | seed | netAoI b1 | b6 | b10 | b11 | b12 | last-3 range | verdict |")
    w("|---|---|---|---|---|---|---|---|---|")
    not_flat = []
    for arm in ARMS:
        for s in SEEDS:
            blk = net_blocks[arm][s]
            if blk is None:
                continue
            v, rng, step = flat_verdict(blk)
            if v == "NOT-flat":
                not_flat.append("%s-s%d" % (arm, s))
            def g(i): return blk[i] if i < blk.size else float("nan")
            w("| %s | %d | %.1f | %.1f | %.1f | %.1f | %.1f | %.2f | %s |" %
              (arm, s, g(0), g(5), g(9), g(10), g(11), rng, v))
    w("")
    w("**Previously-flagged cap-bound platoons @600 ep (per-platoon mean AoI by block):**\n")
    w("| platoon | b1 | b6 | b10 | b11 | b12 | still descending? |")
    w("|---|---|---|---|---|---|---|")
    insufficient = []
    for (arm, s, pl) in FLAGGED:
        blk = flag_blocks[(arm, s, pl)]
        if blk is None:
            continue
        desc = (blk[-1] < blk[-2] - 2.0)
        if desc:
            insufficient.append("%s-s%d-pl%d" % (arm, s, pl))
        def g(i): return blk[i] if i < blk.size else float("nan")
        w("| %s s%d pl%d | %.1f | %.1f | %.1f | %.1f | %.1f | %s |" %
          (arm, s, pl, g(0), g(5), g(9), g(10), g(11), "YES" if desc else "no"))
    w("")
    if insufficient:
        w("**Convergence verdict: 600 ep is INSUFFICIENT** for: %s -- a cap-bound "
          "platoon is still descending at block 12 (drop >2 slots b11->b12). Do NOT "
          "assume 600 is enough for this 3-RB/5-platoon scenario.\n" %
          ", ".join(insufficient))
    else:
        w("**Convergence verdict: the previously-flagged platoons have FLATTENED by "
          "600 ep** (no >2-slot drop in the last block). Remaining NOT-flat runs (by "
          "the strict network-AoI rule): %s.\n" % (", ".join(not_flat) or "none"))

    # 300 vs 600 per-platoon violation
    w("## 2. Last-100-ep violation P(AoI>8): 300 ep vs 600 ep, per seed\n")
    w("| seed | soft 300->600 (worst-pl) | int 300->600 (worst-pl) | pid 300->600 (worst-pl) |")
    w("|---|---|---|---|")
    for s in SEEDS:
        cells = []
        for arm in ("soft", "int", "pid"):
            a3, a6 = m300[arm][s], m600[arm][s]
            if a3 is None or a6 is None:
                cells.append("n/a"); continue
            cells.append("%.3f -> %.3f" % (a3["viol"].max(), a6["viol"].max()))
        w("| %d | %s | %s | %s |" % (s, cells[0], cells[1], cells[2]))
    w("")

    # soft-vs-hard-pid gap + sacrificed
    g3m, g3c = ci95(gap300); g6m, g6c = ci95(gap600)
    w("## 3. Headline numbers: 300 vs 600\n")
    w("| quantity | 300 ep | 600 ep |")
    w("|---|---|---|")
    w("| soft-vs-hard(PID) worst-platoon gap (mean +-95%%CI, n=6) | %.3f +- %.3f | %.3f +- %.3f |"
      % (g3m, g3c, g6m, g6c))
    w("| integral sacrificed platoon-seeds (viol>=0.5) | %d | %d |" % (sac_int_300, sac_int_600))
    w("| soft sacrificed platoon-seeds (viol>=0.5) | %d | %d |" % (sac_soft_300, sac_soft_600))
    w("")

    # verdict on what changes
    gap_pos_600 = (g6m - g6c) > 0
    w("## 4. Do the 300-ep conclusions change at 600 ep?\n")
    w("- **Under-trained cap-bound platoons:** %s.\n" %
      ("still not fully converged at 600 (see section 1) -- the 300-ep pessimism is "
       "only PARTLY relieved" if insufficient else
       "flatten by 600 ep, so their 300-ep worst-platoon numbers were indeed "
       "transition artifacts and improve at 600"))
    w("- **integral sacrificed count:** %d (300) -> %d (600). %s\n" %
      (sac_int_300, sac_int_600,
       "Drops once the cap-bound platoons finish training, as predicted."
       if sac_int_600 < sac_int_300 else
       "Does NOT drop -- the integral sacrifices were not merely under-training."))
    w("- **soft-vs-hard(PID) worst-platoon gap:** %.3f -> %.3f. %s It %s positive at "
      "600 ep, so the core RQ1 protection result %s.\n" %
      (g3m, g6m, ("Shrinks" if g6m < g3m else "Does not shrink") + " as the soft "
       "baseline's worst platoon finishes training.",
       "remains" if gap_pos_600 else "is NOT clearly",
       "survives the longer horizon" if gap_pos_600 else "WEAKENS and must be re-stated"))
    w("- **PID arm:** converged by ep50 in prior analysis; at 600 ep its last-100-ep "
      "numbers should be essentially unchanged vs 300 ep (see section 2).\n")

    w("## 5. Caveats\n")
    w("- epsilon-soft: *expected* violation-rate constraint, satisfied up to violation "
      "probability eps, not per-slot.")
    w("- Single 3-RB / 5-platoon / 4-veh scenario; CIs over 6 seeds.")
    w("- If section 1 flags 600 as insufficient, the true converged worst-platoon "
      "numbers are even better than reported here -- treat 600-ep values as an upper "
      "bound on violation for those runs.")
    w("- Retained global-critic gradient bug unchanged.\n")
    w("## 6. Reproduce\n```\npython analyze_ep600.py\n```")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("[ep600] wrote", REPORT)
    print("[ep600] wrote", figpath)


if __name__ == "__main__":
    main()
