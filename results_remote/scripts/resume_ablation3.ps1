# =====================================================================
# [RQ1-CMDP #3] ONE-COMMAND idempotent reboot-resume for the global-lambda ablation.
# Relaunches the detached, self-finalizing ablation3_driver.ps1 (skips runs whose
# viol_rate.mat exists; writes report once all 12 done unless sentinel set).
#   powershell -NoProfile -ExecutionPolicy Bypass -File `
#     D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\resume_ablation3.ps1
# Stop-Process any stale driver polling dead runs first. If all 12 viol_rate.mat
# exist but no report (driver timeout exit), run analyze_ablation3.py manually.
# =====================================================================
$ErrorActionPreference = 'Stop'
$HERE = $PSScriptRoot
$REPO = Split-Path -Parent $HERE
$LOG  = Join-Path $REPO "1-ModifiedMADDPGwithTDec\logs"
New-Item -ItemType Directory -Force $LOG | Out-Null
$boot = Join-Path $LOG "ablation3_driver.boot.log"
$p = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",(Join-Path $HERE "ablation3_driver.ps1")) `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $boot -RedirectStandardError ($boot + ".err")
Write-Output ("resume: ablation3_driver relaunched (idempotent; completed runs skipped)  pid=" + $p.Id)
