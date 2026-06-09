# =====================================================================
# [RQ1-CMDP] PID tau/eps PHASE-DIAGRAM driver (30 new runs).
#
# Detached, idempotent (Windows Start-Process; tmux/screen unavailable).
# Re-draws the full tau/eps phase diagram under the PID dual.
#
# Grid: tau {8,10,12} x eps {0.10,0.15} = 6 cells, seeds {2-7}, all
#   --mode hard --dual pid --kp 1.0 --ki 1.0 --kd 0.5 (the stability gains).
# Cell t8e10_pid ALREADY EXISTS (6 runs) -> skipped by the marker check.
# New = 5 cells x 6 seeds = 30 runs. One wave per cell (concurrency 6).
#
# Locked base (do NOT recalibrate): episodes=300, lam_max=20, eta_lam=1.0
# (unused by PID but passed), aoi_floor=0.0. Tag = t{tau}e{100eps}_pid.
# A run is "done" when its .out contains the savemat completion marker.
# Idempotent: any run whose marker exists is skipped instantly.
# After all 36 PID cells are complete, runs the analysis/report finalizer.
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 300
$ETA_LAM  = 1.0
$LAM_MAX  = 20.0
$KP = 1.0; $KI = 1.0; $KD = 0.5
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 360

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "phase_pid_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line; Add-Content -Path $DRIVERLOG -Value $line
}
function RunName($s) { "hard_seed$($s.seed)_$($s.tag)" }

function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"
    $argList = @("-u", "Main.py", "--mode", "hard", "--seed", "$($s.seed)",
                 "--episodes", "$EPISODES", "--tau", "$($s.tau)", "--eps", "$($s.eps)",
                 "--eta_lam", "$ETA_LAM", "--lam_max", "$LAM_MAX", "--aoi_floor", "0.0",
                 "--dual", "pid", "--kp", "$KP", "--ki", "$KI", "--kd", "$KD",
                 "--out_tag", $s.tag)
    $out = Join-Path $LOG "$name.out"
    $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-24} pid={1}" -f $name, $p.Id)
}
function Marker-Present($name) {
    $f = Join-Path $LOG "$name.out"
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}
function Wait-Markers($names, $label) {
    Say "WAIT  $label : need $($names.Count) markers"
    $deadline = (Get-Date).AddMinutes($WAVE_TIMEOUT_MIN)
    while ((Get-Date) -lt $deadline) {
        $done = @($names | Where-Object { Marker-Present $_ }).Count
        if ($done -eq $names.Count) { Say "READY $label : all $done done"; return $true }
        Start-Sleep -Seconds $POLL_SEC
    }
    Say "TIMEOUT $label (proceeding anyway)"; return $false
}
function Run-Wave($label, $specs) {
    $names = @($specs | ForEach-Object { RunName $_ })
    $todo  = @($specs | Where-Object { -not (Marker-Present (RunName $_)) })
    Say "WAVE $label : $($specs.Count) runs, $($todo.Count) to launch"
    foreach ($s in $todo) { Launch-Run $s }
    Wait-Markers $names $label | Out-Null
}
function Cell($tau, $eps, $tag) {
    @(2,3,4,5,6,7 | ForEach-Object { @{seed=$_; tau=$tau; eps=$eps; tag=$tag} })
}

# ---------- 6 cells (t8e10 already exists -> its wave launches 0) ----------
$cells = @(
    @{label='t8e10 (exists)'; specs=(Cell 8  0.10 't8e10_pid')},
    @{label='t8e15';          specs=(Cell 8  0.15 't8e15_pid')},
    @{label='t10e10';         specs=(Cell 10 0.10 't10e10_pid')},
    @{label='t10e15';         specs=(Cell 10 0.15 't10e15_pid')},
    @{label='t12e10';         specs=(Cell 12 0.10 't12e10_pid')},
    @{label='t12e15';         specs=(Cell 12 0.15 't12e15_pid')}
)

Say "================ PID PHASE DRIVER START ================"
Say "repo=$REPO ep=$EPISODES lam_max=$LAM_MAX kp=$KP ki=$KI kd=$KD"
foreach ($c in $cells) { Run-Wave $c.label $c.specs }
Say "================ PID PHASE RUNS COMPLETE ================"

# self-contained finalize (no git): write fig + report once all 36 cells done.
$SENT = Join-Path $LOG "phase_pid.finalized"
if (Test-Path $SENT) {
    Say "finalize sentinel present -> report already written; skipping"
} else {
    Say "running analyze_phase_pid.py -> fig_phase_diagram_pid.png + RQ1_PHASE_PID_REPORT.md"
    & $PY (Join-Path $PSScriptRoot "analyze_phase_pid.py") --seeds 2 3 4 5 6 7 2>&1 |
        ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path $SENT -Value (Get-Date).ToString('s')
        Say "FINALIZE OK -> report + figure written; sentinel set"
    } else {
        Say "FINALIZE returned $LASTEXITCODE (some cells missing; report not written)"
    }
}
Say "================ PID PHASE DRIVER EXIT ================"
