# =====================================================================
# [RQ1-CMDP] Stability-study driver (Task 2): sigma-anneal + PID-Lagrangian.
#
# Runs as ONE detached background process (tmux/screen unavailable on this
# Windows host; this is the documented Start-Process equivalent). Independent
# of the Claude Code / SSH / VS-Code session.
#
# Three arms at the LOCKED base (tau=8 eps=0.10 lam_max=20 ep=300 floor=0.0):
#   A. baseline : EXISTING hard t8e10 seeds 2-7  -> REUSE, never relaunched
#   B. anneal   : --sigma_anneal (integral dual)        tag t8e10_anneal
#   C. pid      : --dual pid --kp1 --ki1 --kd0.5 (sigma const) tag t8e10_pid
# = 12 NEW runs (B,C x seeds 2-7). Concurrency = 6 per wave (one arm per wave).
#
# A run is "done" when its .out log contains the savemat completion marker.
# Idempotent: a run whose marker already exists is skipped instantly, so a
# relaunch after a disconnect re-runs only the missing runs.
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 300
$ETA_LAM  = 1.0       # arm B integral dual rate (matches baseline); unused by PID
$LAM_MAX  = 20.0
$TAU      = 8
$EPS      = 0.10
$KP = 1.0; $KI = 1.0; $KD = 0.5
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 360

$REPO = Split-Path -Parent $PSScriptRoot
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "stability_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line
    Add-Content -Path $DRIVERLOG -Value $line
}

function RunName($s) { "hard_seed$($s.seed)_$($s.tag)" }

function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"
    $argList = @("-u", "Main.py", "--mode", "hard", "--seed", "$($s.seed)",
                 "--episodes", "$EPISODES", "--tau", "$TAU", "--eps", "$EPS",
                 "--eta_lam", "$ETA_LAM", "--lam_max", "$LAM_MAX",
                 "--aoi_floor", "0.0", "--out_tag", $s.tag)
    $argList += $s.extra
    $out = Join-Path $LOG "$name.out"
    $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-22} pid={1}  extra=[{2}]" -f $name, $p.Id, ($s.extra -join ' '))
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

# ---------- arm definitions ----------
$waveB = @(2,3,4,5,6,7 | ForEach-Object { @{seed=$_; tag='t8e10_anneal'; extra=@('--sigma_anneal')} })
$waveC = @(2,3,4,5,6,7 | ForEach-Object { @{seed=$_; tag='t8e10_pid';
            extra=@('--dual','pid','--kp',"$KP",'--ki',"$KI",'--kd',"$KD")} })

Say "================ STABILITY DRIVER START ================"
Say "repo=$REPO  ep=$EPISODES tau=$TAU eps=$EPS eta_lam=$ETA_LAM lam_max=$LAM_MAX kp=$KP ki=$KI kd=$KD"

Run-Wave "B (anneal seeds 2-7)" $waveB
Run-Wave "C (pid seeds 2-7)"    $waveC

Say "================ STABILITY COMPLETE ================"

# [RQ1-CMDP] Self-contained finalize: once all 12 runs are done, write the report
# + figures ON DISK (no git). Makes a reboot-relaunch of THIS driver self-
# finalizing, independent of the agent session. Idempotent via the sentinel.
$SENT = Join-Path $LOG "stability.finalized"
if (Test-Path $SENT) {
    Say "finalize sentinel present -> report already written; skipping"
} else {
    Say "running finalize_stability.py -> RQ1_STABILITY_REPORT.md + figures"
    & $PY (Join-Path $PSScriptRoot "finalize_stability.py") --seeds 2 3 4 5 6 7 --tau 8 2>&1 |
        ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path $SENT -Value (Get-Date).ToString('s')
        Say "FINALIZE OK -> report + figures written; sentinel set"
    } else {
        Say "FINALIZE returned $LASTEXITCODE (some runs missing; report not written)"
    }
}
Say "================ DRIVER EXIT ================"
