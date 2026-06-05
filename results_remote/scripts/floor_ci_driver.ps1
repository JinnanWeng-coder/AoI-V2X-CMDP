# =====================================================================
# [RQ1-CMDP] EXP1 (PID+aoi_floor) + EXP2 (CI seeds 8-11) driver.
#
# Detached, idempotent (Windows Start-Process; tmux/screen unavailable).
# Processes a flat, PRIORITY-ORDERED spec list in waves of <=6 (skips any run
# whose completion marker exists). Priority: Exp1 floor + soft + PID arms first,
# integral arm last (so if GPU time is tight the key comparisons land first).
#
# Locked base (do NOT recalibrate): episodes=300, eta_lam=1.0, lam_max=20,
# PID gains kp=1.0 ki=1.0 kd=0.5, scenario 5 platoons x 4 veh x 3 RB.
#
# Runs (31 new):
#  EXP1 (3):  hard pid t8e10 --aoi_floor 0.005, seeds {2,3,4}  tag t8e10_pid_floor
#  EXP2 soft (4):  soft seeds {8,9,10,11}                       tag base
#  EXP2 pid (12):  hard pid {t8e10,t10e10,t12e10} seeds {8..11} tag t{T}e10_pid
#  EXP2 int (12):  hard integral {t8e10,t10e10,t12e10} s {8..11} tag t{T}e10
# A run is "done" when its .out contains the savemat completion marker.
# After all are complete, runs analyze_floor_ci.py (fig + report; no git).
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 300
$ETA_LAM  = 1.0
$LAM_MAX  = 20.0
$KP = 1.0; $KI = 1.0; $KD = 0.5
$MAXCONC = 6
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 360

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "floor_ci_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line; Add-Content -Path $DRIVERLOG -Value $line
}
function RunName($s) { "$($s.mode)_seed$($s.seed)_$($s.tag)" }

function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"
    if ($s.mode -eq 'soft') {
        $argList = @("-u","Main.py","--mode","soft","--seed","$($s.seed)",
                     "--episodes","$EPISODES","--out_tag",$s.tag)
    } else {
        $argList = @("-u","Main.py","--mode","hard","--seed","$($s.seed)",
                     "--episodes","$EPISODES","--tau","$($s.tau)","--eps","$($s.eps)",
                     "--eta_lam","$ETA_LAM","--lam_max","$LAM_MAX",
                     "--aoi_floor","$($s.floor)","--dual",$s.dual,
                     "--kp","$KP","--ki","$KI","--kd","$KD","--out_tag",$s.tag)
    }
    $out = Join-Path $LOG "$name.out"
    $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-28} pid={1}" -f $name, $p.Id)
}
function Marker-Present($name) {
    $f = Join-Path $LOG "$name.out"
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}
function Wait-Markers($names, $label) {
    $deadline = (Get-Date).AddMinutes($WAVE_TIMEOUT_MIN)
    while ((Get-Date) -lt $deadline) {
        $done = @($names | Where-Object { Marker-Present $_ }).Count
        if ($done -eq $names.Count) { Say "READY $label : all $done done"; return }
        Start-Sleep -Seconds $POLL_SEC
    }
    Say "TIMEOUT $label (proceeding anyway)"
}

# ---------- build spec list (priority order) ----------
function HSpec($seed,$tau,$eps,$tag,$dual,$floor){ @{mode='hard';seed=$seed;tau=$tau;eps=$eps;tag=$tag;dual=$dual;floor=$floor} }
function SSpec($seed){ @{mode='soft';seed=$seed;tag='base'} }

$specs = @()
# EXP1: PID + aoi_floor on seeds 2,3,4
foreach ($s in 2,3,4) { $specs += (HSpec $s 8 0.10 't8e10_pid_floor' 'pid' 0.005) }
# EXP2 soft baseline seeds 8-11
foreach ($s in 8,9,10,11) { $specs += (SSpec $s) }
# EXP2 PID arm seeds 8-11 x {t8e10,t10e10,t12e10}
foreach ($s in 8,9,10,11) { foreach ($t in 8,10,12) { $specs += (HSpec $s $t 0.10 ("t{0}e10_pid" -f $t) 'pid' 0.0) } }
# EXP2 integral arm seeds 8-11 x {t8e10,t10e10,t12e10}
foreach ($s in 8,9,10,11) { foreach ($t in 8,10,12) { $specs += (HSpec $s $t 0.10 ("t{0}e10" -f $t) 'integral' 0.0) } }

Say "================ FLOOR+CI DRIVER START ================"
Say "specs=$($specs.Count)  ep=$EPISODES eta=$ETA_LAM lam_max=$LAM_MAX kp=$KP ki=$KI kd=$KD maxconc=$MAXCONC"

# process in waves of MAXCONC, skipping already-complete runs
$todo = @($specs | Where-Object { -not (Marker-Present (RunName $_)) })
$skipped = $specs.Count - $todo.Count
Say "to launch: $($todo.Count)  (skipped already-complete: $skipped)"
$wave = 0
for ($i = 0; $i -lt $todo.Count; $i += $MAXCONC) {
    $wave++
    $chunk = $todo[$i..([Math]::Min($i+$MAXCONC-1, $todo.Count-1))]
    $names = @($chunk | ForEach-Object { RunName $_ })
    Say "WAVE $wave : launching $($chunk.Count) -> $($names -join ', ')"
    foreach ($s in $chunk) { Launch-Run $s }
    Wait-Markers $names "wave$wave"
}
Say "================ FLOOR+CI RUNS COMPLETE ================"

$SENT = Join-Path $LOG "floor_ci.finalized"
if (Test-Path $SENT) {
    Say "finalize sentinel present -> report already written; skipping"
} else {
    Say "running analyze_floor_ci.py -> fig_pid_floor.png + RQ1_FLOOR_AND_CI_REPORT.md"
    & $PY (Join-Path $PSScriptRoot "analyze_floor_ci.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path $SENT -Value (Get-Date).ToString('s')
        Say "FINALIZE OK -> report + figure written; sentinel set"
    } else {
        Say "FINALIZE returned $LASTEXITCODE (some runs missing; report not written)"
    }
}
Say "================ FLOOR+CI DRIVER EXIT ================"
