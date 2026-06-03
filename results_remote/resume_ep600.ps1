# =====================================================================
# [RQ1-CMDP] ONE-COMMAND idempotent reboot-resume for the 600-ep re-run.
# Relaunches the detached, self-finalizing ep600_driver.ps1 (skips runs whose
# completion marker exists; writes report+figure once all 18 done unless the
# sentinel is set). Hidden, orphaned Start-Process -> independent of shell.
#   powershell -NoProfile -ExecutionPolicy Bypass -File `
#     D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\resume_ep600.ps1
# =====================================================================
$ErrorActionPreference = 'Stop'
$HERE = $PSScriptRoot
$REPO = Split-Path -Parent $HERE
$LOG  = Join-Path $REPO "1-ModifiedMADDPGwithTDec\logs"
New-Item -ItemType Directory -Force $LOG | Out-Null
$boot = Join-Path $LOG "ep600_driver.boot.log"
$p = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",(Join-Path $HERE "ep600_driver.ps1")) `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $boot -RedirectStandardError ($boot + ".err")
Write-Output ("resume: ep600_driver relaunched (idempotent; completed runs skipped)  pid=" + $p.Id)
