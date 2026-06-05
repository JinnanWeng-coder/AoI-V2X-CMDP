# =====================================================================
# [RQ1-CMDP] Phase-diagram seed-extension driver (Task 2).
#
# Extends the (tau,eps) grid from seeds {2,3,4} to {2,3,4,5,6,7} by running
# ONLY the missing (cell x seed) combinations for seeds {5,6,7}. Idempotent:
# any run whose completion marker already exists is skipped (so t8e10 s5/6/7,
# already produced by the headline Wave B, are NOT re-run -> only 15 new runs).
#
# Same detached / disconnect-proof pattern as campaign_driver.ps1
# (tmux/screen unavailable on this Windows host): ONE hidden background
# process, file-based completion markers, concurrency <= 6 per wave.
#
# Locked config (do NOT change): episodes=300, eta_lam=1.0, lam_max=20,
# aoi_floor=0.0. Each run gets its own RQ1_CKPT_SUBDIR so they never collide.
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 300
$ETA_LAM  = 1.0
$LAM_MAX  = 20.0
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 360

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "phase_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line
    Add-Content -Path $DRIVERLOG -Value $line
}

function RunName($s) { "$($s.mode)_seed$($s.seed)_$($s.tag)" }

function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"
    $argList = @("-u", "Main.py", "--mode", $s.mode, "--seed", "$($s.seed)",
                 "--episodes", "$EPISODES", "--tau", "$($s.tau)", "--eps", "$($s.eps)",
                 "--eta_lam", "$ETA_LAM", "--lam_max", "$LAM_MAX",
                 "--aoi_floor", "$($s.floor)", "--out_tag", $s.tag)
    $out = Join-Path $LOG "$name.out"
    $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-26} pid={1}" -f $name, $p.Id)
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

function HardSpec($seed, $tau, $eps, $tag) { @{mode='hard'; seed=$seed; tau=$tau; eps=$eps; floor=0.0; tag=$tag} }

# 5 cells x seeds {5,6,7}; t8e10 s5/6/7 already exist (Wave B) -> skipped by idempotency.
$waveP1 = @(5,6,7 | ForEach-Object { HardSpec $_ 8  0.15 't8e15' })  + @(5,6,7 | ForEach-Object { HardSpec $_ 10 0.10 't10e10' })
$waveP2 = @(5,6,7 | ForEach-Object { HardSpec $_ 10 0.15 't10e15' }) + @(5,6,7 | ForEach-Object { HardSpec $_ 12 0.10 't12e10' })
$waveP3 = @(5,6,7 | ForEach-Object { HardSpec $_ 12 0.15 't12e15' })

Say "================ PHASE DRIVER START ================"
Say "repo=$REPO  episodes=$EPISODES eta_lam=$ETA_LAM lam_max=$LAM_MAX  (seeds 5,6,7 x 5 missing cells)"

Run-Wave "P1 (t8e15 + t10e10 seeds 5,6,7)"  $waveP1
Run-Wave "P2 (t10e15 + t12e10 seeds 5,6,7)" $waveP2
Run-Wave "P3 (t12e15 seeds 5,6,7)"          $waveP3

Say "================ PHASE DRIVER COMPLETE ================"

# Self-contained finalize: figures + 6-seed CI table + report splice (NO git/push).
# On reboot-resume this runs after the remaining runs finish; its marker-wait
# passes instantly since all runs are then done. Idempotent.
Say "invoking finalize_phase.ps1 (figures + report, no commit/push)"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "finalize_phase.ps1")
