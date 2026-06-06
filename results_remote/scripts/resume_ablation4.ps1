# =====================================================================
# [RQ1-CMDP #4] ONE-COMMAND idempotent reboot-resume for the fixed-weight ablation.
# Relaunches the detached, self-finalizing ablation4_driver.ps1 (skips runs whose
# viol_rate.mat exists; writes report once all 24 done unless sentinel set).
#   powershell -NoProfile -ExecutionPolicy Bypass -File `
#     D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\scripts\resume_ablation4.ps1
# Stop-Process any stale driver polling dead runs first. If all 24 viol_rate.mat
# exist but no report (driver timeout exit), run analyze_ablation4.py manually.
# (scripts/ is 2 levels under repo.)
# =====================================================================
$ErrorActionPreference = 'Stop'
$HERE = $PSScriptRoot
$REPO = Split-Path -Parent (Split-Path -Parent $HERE)
$LOG  = Join-Path $REPO "1-ModifiedMADDPGwithTDec\logs"
New-Item -ItemType Directory -Force $LOG | Out-Null
$boot = Join-Path $LOG "ablation4_driver.boot.log"
$p = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",(Join-Path $HERE "ablation4_driver.ps1")) `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $boot -RedirectStandardError ($boot + ".err")
Write-Output ("resume: ablation4_driver relaunched (idempotent; completed runs skipped)  pid=" + $p.Id)
