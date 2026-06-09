# =====================================================================
# [RQ1-CMDP] Autonomous finalizer: waits for the 15 added phase runs
# (seeds 5,6,7 x {t8e15,t10e10,t10e15,t12e10,t12e15}) to finish, then
# regenerates the figures + the 6-seed CI phase table and splices it into
# results_remote/RQ1_REMOTE_REPORT.md. Does NOT git-commit and does NOT push.
#
# Used two ways, both disconnect/reboot proof:
#   (a) launched standalone, detached, right after phase_driver.ps1 (handles the
#       no-reboot case where the already-running old driver exits without finalize);
#   (b) called at the end of phase_driver.ps1 (handles reboot-resume: relaunching
#       the driver finishes remaining runs, then finalizes). Its wait passes
#       instantly when the runs are already done. Idempotent overwrite either way.
# =====================================================================
$ErrorActionPreference = 'Stop'
$POLL_SEC = 30
$WAIT_TIMEOUT_MIN = 480

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$RR   = Join-Path $REPO "results_remote"
$LOG  = Join-Path $REPO "1-ModifiedMADDPGwithTDec\logs"
$FLOG = Join-Path $LOG "finalize.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line
    Add-Content -Path $FLOG -Value $line
}

# the 15 added runs that gate finalization (pre-existing 21 hard phase runs already done)
$need = @()
foreach ($tag in 't8e15','t10e10','t10e15','t12e10','t12e15') {
    foreach ($s in 5,6,7) { $need += "hard_seed${s}_${tag}" }
}

function Marker-Present($name) {
    $f = Join-Path $LOG "$name.out"
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}

Say "================ FINALIZE START ================ (waiting for $($need.Count) markers)"
$deadline = (Get-Date).AddMinutes($WAIT_TIMEOUT_MIN)
while ((Get-Date) -lt $deadline) {
    $done = @($need | Where-Object { Marker-Present $_ }).Count
    if ($done -eq $need.Count) { Say "all $done/$($need.Count) markers present"; break }
    Start-Sleep -Seconds $POLL_SEC
}
$done = @($need | Where-Object { Marker-Present $_ }).Count
if ($done -ne $need.Count) { Say "TIMEOUT: only $done/$($need.Count) markers — finalizing anyway with what exists"; }

# 1) refresh the seed-2..7 figures (headline/cost/lambda use t8e10 s2-7; floor uses s2,3,4)
Say "running make_figures.py --seeds 2 3 4 5 6 7 --grid_seeds 2 3 4"
& $PY (Join-Path $PSScriptRoot "make_figures.py") --seeds 2 3 4 5 6 7 --grid_seeds 2 3 4 *>> (Join-Path $LOG "finalize.out")

# 2) regenerate fig_phase_diagram.png (6 seeds) + splice the 6-seed CI table into the report
Say "running finalize_report.py (phase analysis + report splice)"
& $PY (Join-Path $PSScriptRoot "finalize_report.py") *>> (Join-Path $LOG "finalize.out")

Say "================ FINALIZE COMPLETE ================ (no git commit/push — left to operator)"
