# [RQ1-CMDP] Detached run launcher (survives operator disconnect).
# Each run is an independent OS process (Start-Process, hidden window) writing
# clean UTF-8 stdout/stderr logs UNDER the repo. Concurrency is controlled by
# how many specs you pass per call. All paths stay inside the repo subtree.
#
# Usage:
#   $specs = @(
#     @{mode='soft'; seed=2; tau=8;  eps=0.10; floor=0.0;   tag='base'},
#     @{mode='hard'; seed=2; tau=8;  eps=0.10; floor=0.0;   tag='t8e10'}
#   )
#   powershell -File launch_runs.ps1   (after editing $specs below)  -- OR dot-source & call Launch
param(
    [int]$episodes = 300,
    [double]$eta_lam = 1.0,
    [double]$lam_max = 20.0
)

$ErrorActionPreference = 'Stop'
$REPO = Split-Path -Parent $PSScriptRoot      # repo root (results_remote is under it)
$PY  = Join-Path $REPO ".venv\Scripts\python.exe"
$WD  = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$LOG = Join-Path $WD "logs"
New-Item -ItemType Directory -Force $LOG | Out-Null

function Launch-Run($mode, $seed, $tau, $eps, $floor, $tag) {
    $name = "${mode}_seed${seed}_${tag}"
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_${name}"
    $argList = @("-u", "Main.py", "--mode", $mode, "--seed", "$seed", "--episodes", "$episodes",
                 "--tau", "$tau", "--eps", "$eps", "--eta_lam", "$eta_lam",
                 "--lam_max", "$lam_max", "--aoi_floor", "$floor", "--out_tag", $tag)
    $out = Join-Path $LOG "$name.out"
    $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Write-Output ("launched {0,-28} pid={1}  ckpt={2}" -f $name, $p.Id, $env:RQ1_CKPT_SUBDIR)
}

# $specs is expected to be defined by the caller (dot-source) before invoking.
if ($specs) {
    foreach ($s in $specs) {
        Launch-Run $s.mode $s.seed $s.tau $s.eps $s.floor $s.tag
    }
}
