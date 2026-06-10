# =====================================================================
# [RQ1-CMDP] ONE-COMMAND idempotent reboot-resume for the WARM eval-only rerun.
# Relaunches the detached, self-finalizing deploy_warm_driver.ps1 (skips runs whose warm
# eval finished — viol_rate_test_warm_holdout_s14.mat present; writes report once all 12 done).
#   powershell -NoProfile -ExecutionPolicy Bypass -File `
#     D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\scripts\resume_deploy_warm.ps1
# Stop-Process any stale driver first. If all 12 warm-complete but no report, run
# analyze_deploy_warm.py manually. (scripts/ 2 levels under repo.)
# =====================================================================
$ErrorActionPreference = 'Stop'
$HERE = $PSScriptRoot
$REPO = Split-Path -Parent (Split-Path -Parent $HERE)
$LOG  = Join-Path $REPO "1-ModifiedMADDPGwithTDec\logs"
New-Item -ItemType Directory -Force $LOG | Out-Null
$boot = Join-Path $LOG "deploy_warm_driver.boot.log"
$p = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",(Join-Path $HERE "deploy_warm_driver.ps1")) `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $boot -RedirectStandardError ($boot + ".err")
Write-Output ("resume: deploy_warm_driver relaunched (idempotent; completed runs skipped)  pid=" + $p.Id)
