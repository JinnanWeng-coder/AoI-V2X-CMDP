"""Generate MANIFEST.txt for all_runs_mat.tar.gz (run dirs + .mat list + tag decode)."""
import os, re, glob

MODEL = os.path.join(os.path.dirname(__file__), "..", "..",
                     "1-ModifiedMADDPGwithTDec", "model")
OUT = os.path.join(os.path.dirname(__file__), "MANIFEST.txt")

MAT_ORDER = ["AoI", "AoI_evolution", "viol_rate", "lambda", "power",
             "demand", "V2I", "V2V", "Jain",
             "reward_t1", "reward_t2", "reward_global"]


def decode(tag):
    seed = re.search(r"seed(\d+)", tag).group(1)
    if tag.startswith("marl_model_soft"):
        return f"mode=soft (baseline)  seed={seed}  (tau/eps N/A -- soft policy is tau-independent)"
    tau = re.search(r"_t(\d+)e", tag).group(1)
    e100 = int(re.search(r"_t\d+e(\d+)", tag).group(1))
    eps = f"{e100/100:.2f}"
    floor = "aoi_floor=0.005" if tag.endswith("_floor") else "aoi_floor=0.0"
    return f"mode=hard  tau={tau}  eps={eps}  seed={seed}  {floor}"


dirs = sorted(d for d in os.listdir(MODEL)
              if d.startswith("marl_model_") and os.path.isdir(os.path.join(MODEL, d)))

lines = []
lines.append("MANIFEST -- all_runs_mat.tar.gz")
lines.append("AoI-V2X-CMDP RQ1 remote campaign raw .mat outputs (30 runs, 300 ep each).")
lines.append("Archive: results_remote/raw/all_runs_mat.tar.gz  (gzip; paths preserved as marl_model_<tag>/<name>.mat)")
lines.append("")
lines.append("Unpack (from results_remote/raw/):")
lines.append("    tar --force-local -xzf all_runs_mat.tar.gz -C <dest>")
lines.append("  -> recreates marl_model_<tag>/*.mat under <dest>.")
lines.append("")
lines.append("Tag encoding:  hard_seed<N>_t<TAU>e<100*EPS>[_floor]   |   soft_seed<N>_base")
lines.append("  mode  : 'hard' = per-platoon CMDP P(AoI_j>tau)<=eps ;  'soft' = AoI as -AoI/20 reward penalty (baseline, tau/eps-independent)")
lines.append("  tau   : AoI threshold (slots).   eps : target per-platoon violation probability.")
lines.append("  floor : suffix '_floor' => --aoi_floor 0.005 (Exp2 feasibility safeguard); absent => 0.0 (default).")
lines.append("  Locked config for every run: episodes=300, eta_lam=1.0, lam_max=20.  Env: torch 2.6+cu126 / numpy 2.2.4, RTX 4090.")
lines.append("")
lines.append(".mat files per run (12): " + ", ".join(MAT_ORDER))
lines.append("")
lines.append("=" * 78)

total_mat = 0
for d in dirs:
    mats = sorted(glob.glob(os.path.join(MODEL, d, "*.mat")))
    total_mat += len(mats)
    lines.append(f"[{d}/]  ->  {decode(d)}")
    for m in mats:
        sz = os.path.getsize(m)
        lines.append(f"      {os.path.basename(m):20s} {sz:>9d} bytes")
    lines.append("")

lines.append("=" * 78)
lines.append(f"Total run dirs: {len(dirs)}   Total .mat files: {total_mat}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"WROTE {OUT}  ({len(lines)} lines, {len(dirs)} dirs, {total_mat} .mat)")
