# =====================================================================
# [RQ1-CMDP] t8e10 three-arm 600-episode re-run (18 runs).
#
# WHY: three 300-ep t8e10 runs (soft-s2, hard-int-s3, hard-int-s7) are
# UNDER-TRAINED -- a cap-bound platoon is still descending at ep300, so their
# last-100-ep window sits mid-transition. Main.py trains from scratch (no
# resume), so "extend" = re-run at --episodes 600. NEW _ep600 tags so the
# existing 300-ep runs are NOT overwritten.
#
# Detached, idempotent (Windows Start-Process; tmux/screen unavailable).
# Locked config UNCHANGED except episodes: eta_lam=1.0, lam_max=20, tau=8,
# eps=0.10, PID gains kp=1.0 ki=1.0 kd=0.5, scenario 5 platoons x 4 veh x 3 RB,
# sigma const 0.3 (NO --sigma_anneal). 3 arms x 6 seeds, waves of <=6.
#   A soft          tag base_ep600
#   B hard integral tag t8e10_ep600
#   C hard pid      tag t8e10_pid_ep600
# A run is "done" when its .out contains the savemat completion marker.
# After all 18 complete, runs analyze_ep600.py (report + figure; no git).
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 600
$ETA_LAM  = 1.0
$LAM_MAX  = 20.0
$KP = 1.0; $KI = 1.0; $KD = 0.5
$MAXCONC = 6
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 600

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "ep600_driver.progress.log"
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
function Wait-Markers($names, $label) {
    $deadline = (Get-Date).AddMinutes($WAVE_TIMEOUT_MIN)
    while ((Get-Date) -lt $deadline) {
        $done = @($names | Where-Object { Marker-Present $_ }).Count
        if ($done -eq $names.Count) { Say "READY $label : all $done done"; return }
        Start-Sleep -Seconds $POLL_SEC
    }
    Say "TIMEOUT $label (proceeding anyway)"
}

function SSpec($seed){ @{mode='soft';seed=$seed;tag='base_ep600'} }
function HSpec($seed,$dual,$tag){ @{mode='hard';seed=$seed;dual=$dual;tag=$tag} }

$specs = @()
foreach ($s in 2,3,4,5,6,7) { $specs += (SSpec $s) }                       # A soft
foreach ($s in 2,3,4,5,6,7) { $specs += (HSpec $s 'integral' 't8e10_ep600') }  # B int
foreach ($s in 2,3,4,5,6,7) { $specs += (HSpec $s 'pid' 't8e10_pid_ep600') }   # C pid

Say "================ EP600 DRIVER START ================"
Say "specs=$($specs.Count) ep=$EPISODES eta=$ETA_LAM lam_max=$LAM_MAX kp=$KP ki=$KI kd=$KD maxconc=$MAXCONC"
$todo = @($specs | Where-Object { -not (Marker-Present (RunName $_)) })
Say "to launch: $($todo.Count) (skipped already-complete: $($specs.Count - $todo.Count))"
$wave = 0
for ($i = 0; $i -lt $todo.Count; $i += $MAXCONC) {
    $wave++
    $chunk = $todo[$i..([Math]::Min($i+$MAXCONC-1, $todo.Count-1))]
    $names = @($chunk | ForEach-Object { RunName $_ })
    Say "WAVE $wave : launching $($chunk.Count) -> $($names -join ', ')"
    foreach ($s in $chunk) { Launch-Run $s }
    Wait-Markers $names "wave$wave"
}
Say "================ EP600 RUNS COMPLETE ================"

$SENT = Join-Path $LOG "ep600.finalized"
if (Test-Path $SENT) {
    Say "finalize sentinel present -> report already written; skipping"
} else {
    Say "running analyze_ep600.py -> fig_ep600_convergence.png + RQ1_EP600_REPORT.md"
    & $PY (Join-Path $PSScriptRoot "analyze_ep600.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path $SENT -Value (Get-Date).ToString('s')
        Say "FINALIZE OK -> report + figure written; sentinel set"
    } else {
        Say "FINALIZE returned $LASTEXITCODE (some runs missing; report not written)"
    }
}
Say "================ EP600 DRIVER EXIT ================"
