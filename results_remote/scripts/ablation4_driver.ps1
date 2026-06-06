# =====================================================================
# [RQ1-CMDP #4] Qu-style FIXED-WEIGHT threshold-penalty arm (24 runs).
#
# Isolates "constraint vs penalty" at IDENTICAL signal: the SAME indicator
# 1{AoI>tau} as the hard CMDP, but a FIXED reward weight and NO dual.
# Runs in --mode soft (lambda stays 0). The soft baseline (base_ep600) and the
# per-platoon hard PID arm (t8e10_pid_ep600) ALREADY EXIST -> NOT re-run here.
#
# Sweep w in {2,5,10,20} x seeds {2-7} = 24 runs, tau=8 (indicator fires at the
# SAME threshold as the hard constraint), episodes=600. Run dirs:
#   marl_model_soft_seed<seed>_qind_w<w>_ep600
# Locked otherwise; do NOT touch the dual / cost critic.
#
# Detached, idempotent: a run is SKIPPED if its model dir's viol_rate.mat exists
# (or its .out has the savemat marker). Concurrency <=6 (4 waves, one per weight).
# After all 24 complete, runs analyze_ablation4.py.
# NOTE: this script lives in results_remote/scripts/ -> repo root is TWO levels up.
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 600
$TAU      = 8
$WEIGHTS  = 2,5,10,20
$MAXCONC  = 6
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 1440

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # scripts/ is 2 levels under repo
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$MODEL= Join-Path $WD "model"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "ablation4_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line; Add-Content -Path $DRIVERLOG -Value $line
}
function RunName($s) { "soft_seed$($s.seed)_$($s.tag)" }
function Run-Done($s) {
    $vr = Join-Path $MODEL ("marl_model_" + (RunName $s) + "\viol_rate.mat")
    if (Test-Path $vr) { return $true }
    $f = Join-Path $LOG ((RunName $s) + ".out")
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}
function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"
    $argList = @("-u","Main.py","--mode","soft","--episodes","$EPISODES",
                 "--seed","$($s.seed)","--tau","$TAU",
                 "--aoi_pen_type","indicator","--aoi_pen_w","$($s.w)",
                 "--out_tag",$s.tag)
    $out = Join-Path $LOG "$name.out"
    $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-34} pid={1}" -f $name, $p.Id)
}

$specs = @()
foreach ($w in $WEIGHTS) { foreach ($sd in 2,3,4,5,6,7) {
    $specs += @{seed=$sd; w=$w; tag=("qind_w{0}_ep600" -f $w)} } }

Say "================ ABLATION#4 DRIVER START ================"
Say "ep=$EPISODES tau=$TAU weights=$($WEIGHTS -join ',') maxconc=$MAXCONC  (24 runs)"
$todo = @($specs | Where-Object { -not (Run-Done $_) })
Say "to launch: $($todo.Count) (skipped already-complete: $($specs.Count - $todo.Count))"
$wave = 0
for ($i = 0; $i -lt $todo.Count; $i += $MAXCONC) {
    $wave++
    $chunk = $todo[$i..([Math]::Min($i+$MAXCONC-1, $todo.Count-1))]
    Say "WAVE $wave : launching $($chunk.Count) -> $(@($chunk | ForEach-Object { RunName $_ }) -join ', ')"
    foreach ($s in $chunk) { Launch-Run $s }
    $deadline = (Get-Date).AddMinutes($WAVE_TIMEOUT_MIN)
    while ((Get-Date) -lt $deadline) {
        $done = @($chunk | Where-Object { Run-Done $_ }).Count
        if ($done -eq $chunk.Count) { Say "READY wave$wave : all $done done"; break }
        Start-Sleep -Seconds $POLL_SEC
    }
}
Say "================ ABLATION#4 RUNS COMPLETE ================"

$SENT = Join-Path $LOG "ablation4.finalized"
if (Test-Path $SENT) {
    Say "finalize sentinel present -> report already written; skipping"
} else {
    Say "running analyze_ablation4.py -> RQ1_ABLATION4_FIXEDWEIGHT.md"
    & $PY (Join-Path $PSScriptRoot "analyze_ablation4.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path $SENT -Value (Get-Date).ToString('s')
        Say "FINALIZE OK -> report written; sentinel set"
    } else {
        Say "FINALIZE returned $LASTEXITCODE (runs missing; report not written)"
    }
}
Say "================ ABLATION#4 DRIVER EXIT ================"
