# =====================================================================
# [RQ1-CMDP] Detached SELF-CONTAINED finalizer-watcher for Task 2.
#
# Independent of the agent session / SSH (launched as a hidden, orphaned
# Start-Process). Polls for ALL 12 run-completion markers (anneal + pid,
# seeds 2-7); once present, runs finalize_stability.py to generate the two
# figures and write results_remote/RQ1_STABILITY_REPORT.md ON DISK.
#
# Does NOT touch git (commit/push is left to the operator).
# Idempotent: writes a .finalized sentinel and exits; a relaunch that finds
# the sentinel exits immediately. Safe to relaunch after a reboot.
# =====================================================================
$ErrorActionPreference = 'Stop'
$POLL_SEC = 30
$TIMEOUT_MIN = 600

$REPO = Split-Path -Parent $PSScriptRoot
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$LOG  = Join-Path $WD "logs"
$WLOG = Join-Path $LOG "stability_finalize_watch.log"
$SENT = Join-Path $LOG "stability.finalized"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($m) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $m
    Write-Output $line; Add-Content -Path $WLOG -Value $line
}
function Marker-Present($name) {
    $f = Join-Path $LOG "$name.out"
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}

$need = @()
foreach ($s in 2..7) { $need += "hard_seed${s}_t8e10_anneal" }
foreach ($s in 2..7) { $need += "hard_seed${s}_t8e10_pid" }

Say "================ FINALIZE-WATCH START ================"
if (Test-Path $SENT) { Say "sentinel present -> already finalized; exit"; return }
Say "waiting for $($need.Count) markers (anneal + pid, seeds 2-7)"

$deadline = (Get-Date).AddMinutes($TIMEOUT_MIN)
while ((Get-Date) -lt $deadline) {
    $done = @($need | Where-Object { Marker-Present $_ }).Count
    if ($done -eq $need.Count) {
        Say "all $done markers present -> running finalize_stability.py"
        & $PY (Join-Path $PSScriptRoot "finalize_stability.py") --seeds 2 3 4 5 6 7 --tau 8 2>&1 |
            ForEach-Object { Say "  $_" }
        if ($LASTEXITCODE -eq 0) {
            Set-Content -Path $SENT -Value (Get-Date).ToString('s')
            Say "FINALIZE OK -> RQ1_STABILITY_REPORT.md + figures written; sentinel set"
        } else {
            Say "FINALIZE returned $LASTEXITCODE (report not written; will not loop)"
        }
        Say "================ FINALIZE-WATCH DONE ================"
        return
    }
    Start-Sleep -Seconds $POLL_SEC
}
Say "TIMEOUT waiting for markers ($done/$($need.Count)); exiting without finalize"
