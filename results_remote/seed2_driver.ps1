# =====================================================================
# [RQ1-CMDP] seed2 1000-episode infeasibility test (3 runs, run concurrently).
#
# WHY: ep600 showed the 300-ep "sacrificed" platoons were mostly under-training;
# only seed2-pl2 still looks sacrificed, but it was STILL DESCENDING at ep600
# (block b10=11.7 b11=14.2 b12=11.0). 1000 ep settles whether seed2-pl2 is truly
# resource-limited or just slow to train. Main.py trains from scratch -> re-run at
# --episodes 1000. NEW _ep1000 tags (existing runs untouched).
#
# Detached, idempotent (Windows Start-Process; tmux/screen unavailable).
# Locked config UNCHANGED except episodes: tau=8 eps=0.10 eta_lam=1.0 lam_max=20,
# PID kp=1 ki=1 kd=0.5, sigma const 0.3, scenario 5 platoons x 4 veh x 3 RB.
# SEED 2 only. 3 arms launched together (concurrency 3 <= 6):
#   A soft          tag base_ep1000
#   B hard integral tag t8e10_ep1000
#   C hard pid      tag t8e10_pid_ep1000
# A run is "done" when its .out has 'simulation took this much time'.
# After all 3 complete, runs analyze_seed2.py (report + figure; no git).
# Generous wait timeout (1440 min) so a late resume does not prematurely finalize.
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 1000
$ETA_LAM  = 1.0
$LAM_MAX  = 20.0
$KP = 1.0; $KI = 1.0; $KD = 0.5
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 1440

$REPO = Split-Path -Parent $PSScriptRoot
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "seed2_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line; Add-Content -Path $DRIVERLOG -Value $line
}
function RunName($s) { "$($s.mode)_seed2_$($s.tag)" }

function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"
    if ($s.mode -eq 'soft') {
        $argList = @("-u","Main.py","--mode","soft","--seed","2",
                     "--episodes","$EPISODES","--out_tag",$s.tag)
    } else {
        $argList = @("-u","Main.py","--mode","hard","--seed","2",
                     "--episodes","$EPISODES","--tau","8","--eps","0.10",
                     "--eta_lam","$ETA_LAM","--lam_max","$LAM_MAX","--aoi_floor","0.0",
                     "--dual",$s.dual,"--kp","$KP","--ki","$KI","--kd","$KD","--out_tag",$s.tag)
    }
    $out = Join-Path $LOG "$name.out"
    $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-30} pid={1}" -f $name, $p.Id)
}
function Marker-Present($name) {
    $f = Join-Path $LOG "$name.out"
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}

$specs = @(
    @{mode='soft'; tag='base_ep1000'},
    @{mode='hard'; dual='integral'; tag='t8e10_ep1000'},
    @{mode='hard'; dual='pid';      tag='t8e10_pid_ep1000'}
)

Say "================ SEED2 EP1000 DRIVER START ================"
Say "ep=$EPISODES eta=$ETA_LAM lam_max=$LAM_MAX kp=$KP ki=$KI kd=$KD"
$todo = @($specs | Where-Object { -not (Marker-Present (RunName $_)) })
Say "to launch: $($todo.Count) (skipped already-complete: $($specs.Count - $todo.Count))"
foreach ($s in $todo) { Launch-Run $s }

$names = @($specs | ForEach-Object { RunName $_ })
Say "WAIT : need $($names.Count) markers"
$deadline = (Get-Date).AddMinutes($WAVE_TIMEOUT_MIN)
while ((Get-Date) -lt $deadline) {
    $done = @($names | Where-Object { Marker-Present $_ }).Count
    if ($done -eq $names.Count) { Say "READY : all $done done"; break }
    Start-Sleep -Seconds $POLL_SEC
}
Say "================ SEED2 EP1000 RUNS COMPLETE ================"

$SENT = Join-Path $LOG "seed2.finalized"
if (Test-Path $SENT) {
    Say "finalize sentinel present -> report already written; skipping"
} else {
    Say "running analyze_seed2.py -> fig_seed2_infeas.png + RQ1_SEED2_INFEAS_REPORT.md"
    & $PY (Join-Path $PSScriptRoot "analyze_seed2.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path $SENT -Value (Get-Date).ToString('s')
        Say "FINALIZE OK -> report + figure written; sentinel set"
    } else {
        Say "FINALIZE returned $LASTEXITCODE (runs missing; report not written)"
    }
}
Say "================ SEED2 EP1000 DRIVER EXIT ================"
