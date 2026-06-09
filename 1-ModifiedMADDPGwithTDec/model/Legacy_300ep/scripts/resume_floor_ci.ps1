# =====================================================================
# [RQ1-CMDP] ONE-COMMAND idempotent reboot-resume for EXP1+EXP2 (floor+CI).
# Relaunches the detached, self-finalizing floor_ci_driver.ps1 (skips any run
# whose completion marker exists; writes fig + report once all runs done unless
# the sentinel is set). Hidden, orphaned Start-Process -> independent of shell.
#   powershell -NoProfile -ExecutionPolicy Bypass -File `
#     D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\resume_floor_ci.ps1
# =====================================================================
$ErrorActionPreference = 'Stop'
$HERE = $PSScriptRoot
$REPO = Split-Path -Parent (Split-Path -Parent $HERE)
$LOG  = Join-Path $REPO "1-ModifiedMADDPGwithTDec\logs"
New-Item -ItemType Directory -Force $LOG | Out-Null
$boot = Join-Path $LOG "floor_ci_driver.boot.log"
$p = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",(Join-Path $HERE "floor_ci_driver.ps1")) `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $boot -RedirectStandardError ($boot + ".err")
Write-Output ("resume: floor_ci_driver relaunched (idempotent; completed runs skipped)  pid=" + $p.Id)
