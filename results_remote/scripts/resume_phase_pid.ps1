# =====================================================================
# [RQ1-CMDP] ONE-COMMAND idempotent reboot-resume for the PID phase diagram.
# Relaunches the detached, self-finalizing phase_pid_driver.ps1 (skips any run
# whose completion marker exists -> only missing runs rerun from ep 0; writes
# fig + report once all 36 PID cells are done unless the sentinel is set).
# Hidden, orphaned Start-Process -> independent of this shell / SSH. No git.
#   powershell -NoProfile -ExecutionPolicy Bypass -File `
#     D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\resume_phase_pid.ps1
# =====================================================================
$ErrorActionPreference = 'Stop'
$HERE = $PSScriptRoot
$REPO = Split-Path -Parent (Split-Path -Parent $HERE)
$LOG  = Join-Path $REPO "1-ModifiedMADDPGwithTDec\logs"
New-Item -ItemType Directory -Force $LOG | Out-Null
$boot = Join-Path $LOG "phase_pid_driver.boot.log"
$p = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",(Join-Path $HERE "phase_pid_driver.ps1")) `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $boot -RedirectStandardError ($boot + ".err")
Write-Output ("resume: phase_pid_driver relaunched (idempotent; completed runs skipped)  pid=" + $p.Id)
