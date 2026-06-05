# =====================================================================
# [RQ1-CMDP] ONE-COMMAND idempotent reboot-resume for the seed2 1000-ep test.
# Relaunches the detached, self-finalizing seed2_driver.ps1 (skips runs whose
# completion marker exists; writes report+figure once all 3 done unless the
# sentinel is set). Hidden, orphaned Start-Process -> independent of shell.
#   powershell -NoProfile -ExecutionPolicy Bypass -File `
#     D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\resume_seed2.ps1
# If a stale driver powershell is still polling dead runs, Stop-Process it first.
# If the driver exits before runs finish (timeout), run analyze_seed2.py manually
# once all 3 .out markers exist.
# =====================================================================
$ErrorActionPreference = 'Stop'
$HERE = $PSScriptRoot
$REPO = Split-Path -Parent (Split-Path -Parent $HERE)
$LOG  = Join-Path $REPO "1-ModifiedMADDPGwithTDec\logs"
New-Item -ItemType Directory -Force $LOG | Out-Null
$boot = Join-Path $LOG "seed2_driver.boot.log"
$p = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",(Join-Path $HERE "seed2_driver.ps1")) `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $boot -RedirectStandardError ($boot + ".err")
Write-Output ("resume: seed2_driver relaunched (idempotent; completed runs skipped)  pid=" + $p.Id)
