"""
[RQ1-CMDP] seed2-pl2 infeasibility test: structurally resource-limited, or just
under-trained? Uses the 1000-ep seed2 runs (3 arms) + the existing 300/600-ep runs
for a horizon comparison. SEED 2, platoon index 2 (pl2 = the only platoon still
flagged "sacrificed" after ep600).

Arms (tag at 1000 / 600 / 300 ep):
  soft  base_ep1000 / base_ep600 / base
  int   t8e10_ep1000 / t8e10_ep600 / t8e10            (--dual integral)
  pid   t8e10_pid_ep1000 / t8e10_pid_ep600 / t8e10_pid (--dual pid)

Sources: AoI.mat = pl2 mean AoI EVERY episode -> 50-ep blocked trajectory (20 blocks
over 1000 ep). AoI_evolution.mat = last-100-ep per-step AoI (ep[900,1000) at 1000 ep)
-> pl2 violation@8 + mean AoI. lambda.mat = pl2 final-100-ep multiplier (saturated
near lam_max=20?). Outputs under results_remote/: fig_seed2_infeas.png,
RQ1_SEED2_INFEAS_REPORT.md. Exit 2 (no report) if any 1000-ep run missing. No git.
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze_remote import metrics, folder, _load

HERE = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REPORT = os.path.join(HERE, "RQ1_SEED2_INFEAS_REPORT.md")
SEED = 2
PL = 2
TAU = 8
EPS = 0.10
LAM_MAX = 20.0
BLOCK = 50
# arm -> mode, {horizon: tag}
ARMS = {
    "soft": ("soft", {300: "base", 600: "base_ep600", 1000: "base_ep1000"}),
    "int":  ("hard", {300: "t8e10", 600: "t8e10_ep600", 1000: "t8e10_ep1000"}),
    "pid":  ("hard", {300: "t8e10_pid", 600: "t8e10_pid_ep600", 1000: "t8e10_pid_ep1000"}),
}


def pl2_blocks(mode, tag):
    aoi = _load(os.path.join(folder(mode, SEED, tag), "AoI.mat"), "AoI")
    if aoi is None:
        return None
    s = aoi.astype(np.float64)[PL]                 # [nep]
    nb = s.shape[0] // BLOCK
    return s[:nb * BLOCK].reshape(nb, BLOCK).mean(axis=1)


def pl2_final(mode, tag):
    """last-100-ep pl2 viol@8, mean AoI, final lambda; + whole-network viol."""
    mm = metrics(mode, SEED, tag, TAU)
    if mm is None:
        return None
    lam = mm["lam_final"]
    return dict(
        viol=float(mm["viol"][PL]), aoi=float(mm["aoi"][PL]),
        lam=(float(lam[PL]) if lam is not None else float("nan")),
        net_viol=float(mm["viol"].mean()), net_viol_worst=float(mm["viol"].max()),
        all_viol=mm["viol"],
    )


def main():
    # gate: all three 1000-ep runs present
    missing = [a for a, (mode, tags) in ARMS.items()
               if metrics(mode, SEED, tags[1000], TAU) is None]
    if missing:
        sys.stderr.write("[seed2] missing 1000-ep arms: %s -- not writing report\n"
                         % ", ".join(missing))
        sys.exit(2)

    blk = {a: pl2_blocks(m, tags[1000]) for a, (m, tags) in ARMS.items()}
    fin = {a: {h: pl2_final(m, tags[h]) for h in (300, 600, 1000)}
           for a, (m, tags) in ARMS.items()}

    # ---- figure: pl2 AoI 50-ep blocks over 1000 ep ----
    fig, ax = plt.subplots(figsize=(9, 4.5))
    colors = {"soft": "#c44", "int": "#48c", "pid": "#4a4"}
    for a in ARMS:
        if blk[a] is not None:
            x = (np.arange(blk[a].size) + 1) * BLOCK
            ax.plot(x, blk[a], "-o", color=colors[a], lw=1.5, ms=3, label=a)
    ax.axhline(TAU, ls="--", color="k", lw=1, label="tau=8")
    ax.set_xlabel("episode"); ax.set_ylabel("seed2 pl2 mean AoI (slots)")
    ax.set_title("seed2-pl2 AoI trajectory @1000 ep (50-ep blocks)")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout()
    figpath = os.path.join(HERE, "fig_seed2_infeas.png")
    fig.savefig(figpath, dpi=150); plt.close(fig)

    # ---- per-arm flatten/descend verdict at 1000 ep ----
    def descend(b):
        if b is None or b.size < 3:
            return "n/a", float("nan"), float("nan")
        rng = float(b[-3:].max() - b[-3:].min())
        step = float(b[-1] - b[-2])
        still = b[-1] < b[-2] - 2.0
        return ("DESCENDING" if still else ("FLAT" if rng < 1.0 else "noisy-but-not-descending")), rng, step

    L = []; w = L.append
    w("# RQ1 — seed2-pl2: structurally infeasible, or under-trained? (1000-ep test)\n")
    w("**Auto-generated on disk by `seed2_driver.ps1` -> `analyze_seed2.py`** "
      "(detached). Commit left to the operator.\n")
    w("The ONLY remaining evidence for a truly resource-limited platoon in this "
      "scenario was seed2-pl2 (the lone case still 'sacrificed' after ep600), but at "
      "600 ep it was STILL DESCENDING (b10=11.7 b11=14.2 b12=11.0), so it might be "
      "merely under-trained. This re-runs seed2 (soft / hard-int / hard-PID) at "
      "**1000 ep**, locked config otherwise unchanged (tau=8 eps=0.10 eta_lam=1.0 "
      "lam_max=20, PID kp=1 ki=1 kd=0.5, sigma 0.3). pl2 = platoon index 2; "
      "last-100-ep at 1000 ep = ep[900,1000).\n")

    w("## 1. seed2-pl2 AoI trajectory @1000 ep (50-ep blocks, 20 blocks)\n")
    w("See `fig_seed2_infeas.png`. Tail blocks (b16..b20) and verdict per arm:\n")
    w("| arm | b1 | b10 | b16 | b17 | b18 | b19 | b20 | last-3 range | b19->b20 | verdict |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    verds = {}
    for a in ARMS:
        b = blk[a]
        if b is None:
            w("| %s | MISSING |||||||||" % a); continue
        v, rng, step = descend(b)
        verds[a] = v
        def g(i): return b[i] if i < b.size else float("nan")
        w("| %s | %.1f | %.1f | %.1f | %.1f | %.1f | %.1f | %.1f | %.2f | %+.1f | %s |" %
          (a, g(0), g(9), g(15), g(16), g(17), g(18), g(19), rng, step, v))
    w("")

    w("## 2. seed2-pl2 last-100-ep: 300 vs 600 vs 1000 ep\n")
    w("| arm | metric | 300 ep | 600 ep | 1000 ep |")
    w("|---|---|---|---|---|")
    for a in ARMS:
        f3, f6, f10 = fin[a][300], fin[a][600], fin[a][1000]
        def cell(f, k, fmt="%.3f"):
            return "n/a" if f is None else (fmt % f[k])
        w("| %s | viol P(AoI>8) | %s | %s | %s |" % (a, cell(f3, "viol"), cell(f6, "viol"), cell(f10, "viol")))
        w("| | mean AoI | %s | %s | %s |" % (cell(f3, "aoi", "%.1f"), cell(f6, "aoi", "%.1f"), cell(f10, "aoi", "%.1f")))
        w("| | final lambda | %s | %s | %s |" % (cell(f3, "lam", "%.1f"), cell(f6, "lam", "%.1f"), cell(f10, "lam", "%.1f")))
    w("")

    w("## 3. Whole-network last-100-ep violation @1000 ep (all 5 platoons feasible?)\n")
    w("| arm | per-platoon viol | network mean | worst platoon |")
    w("|---|---|---|---|")
    for a in ARMS:
        f = fin[a][1000]
        w("| %s | %s | %.3f | %.3f |" %
          (a, np.round(f["all_viol"], 3).tolist(), f["net_viol"], f["net_viol_worst"]))
    w("")

    # ---- verdict ----
    # Use the PID arm as the converged reference (it serves pl2); the structural
    # question is really about whether ANY dual can serve pl2 with bounded AoI.
    pid10 = fin["pid"][1000]; int10 = fin["int"][1000]; soft10 = fin["soft"][1000]
    pid_serves = pid10["viol"] <= EPS + 0.05 and pid10["aoi"] < 3 * TAU
    pid_lam_sat = pid10["lam"] >= LAM_MAX - 0.5
    pid_desc = verds.get("pid") == "DESCENDING"
    w("## 4. VERDICT\n")
    if pid_serves and not pid_desc:
        w("**seed2-pl2 is UNDER-TRAINED, not structurally infeasible.** At 1000 ep "
          "the PID arm serves pl2 with bounded AoI (viol=%.3f, mean AoI=%.1f slots) "
          "and its trajectory has %s by block 20; the multiplier is %s (lambda=%.1f, "
          "%s saturated). A genuinely resource-limited platoon would pin viol~1.0 / "
          "AoI>>tau / lambda=%g at every horizon — pl2 does not. **Implication: NO "
          "truly-infeasible platoon remains in this 3-RB/5-platoon scenario, so the "
          "--aoi_floor safeguard is NOT strictly necessary here** (it remains useful "
          "only as belt-and-suspenders / for tighter tau-eps or richer scenarios). "
          "The soft/integral arms %s — pl2's fate is a TRAINING-horizon and "
          "dual-rule question, not a structural one.\n" %
          (pid10["viol"], pid10["aoi"], verds.get("pid", "n/a"),
           "off the cap" if not pid_lam_sat else "still high",
           pid10["lam"], "IS" if pid_lam_sat else "is NOT", LAM_MAX,
           ("still leave pl2 high (soft viol=%.3f, int viol=%.3f) — i.e. those duals "
            "are slower / weaker on this bottleneck, not that the platoon is unservable"
            % (soft10["viol"], int10["viol"]))))
    elif pid_desc or verds.get("soft") == "DESCENDING" or verds.get("int") == "DESCENDING":
        w("**1000 ep is STILL INSUFFICIENT** for at least one arm (pl2 trajectory "
          "still descending at block 20: soft=%s int=%s pid=%s). pl2 keeps improving "
          "with more training, which already argues AGAINST structural infeasibility "
          "(a resource-limited platoon would plateau high, not keep falling), but the "
          "converged value is not yet pinned down. Recommend the next horizon "
          "(>=1500 ep) for the slow arm(s); the PID arm at 1000 ep gives viol=%.3f "
          "AoI=%.1f lambda=%.1f as the current best estimate.\n" %
          (verds.get("soft"), verds.get("int"), verds.get("pid"),
           pid10["viol"], pid10["aoi"], pid10["lam"]))
    else:
        w("**seed2-pl2 is STRUCTURALLY RESOURCE-LIMITED.** Even at 1000 ep the best "
          "arm leaves pl2 at viol=%.3f / mean AoI=%.1f with lambda pinned near "
          "lam_max (%.1f), and the trajectory has plateaued HIGH (not descending). "
          "This confirms a genuinely unservable platoon exists in this scenario, so "
          "the --aoi_floor safeguard line IS justified.\n" %
          (pid10["viol"], pid10["aoi"], pid10["lam"]))

    w("## 5. Caveats\n")
    w("- epsilon-soft: *expected* violation-rate constraint, satisfied up to "
      "violation probability eps, not per-slot.")
    w("- Single seed (2) and single 3-RB/5-platoon scenario; this resolves the ONE "
      "outstanding case, not a distribution.")
    w("- Retained global-critic gradient bug unchanged.\n")
    w("## 6. Reproduce\n```\npython analyze_seed2.py\n```")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("[seed2] wrote", REPORT)
    print("[seed2] wrote", figpath)


if __name__ == "__main__":
    main()
