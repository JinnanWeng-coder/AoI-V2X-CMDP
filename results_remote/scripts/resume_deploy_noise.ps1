# =====================================================================
# [RQ1-CMDP] ONE-COMMAND idempotent reboot-resume for the STOCHASTIC noise eval-only sweep.
# Relaunches the detached, self-finalizing deploy_noise_driver.ps1 (skips any (run,sigma)
# whose viol_rate_test_warm_n<NN>_holdout_s14.mat exists; writes report once all 36 done).
#   powershell -NoProfile -ExecutionPolicy Bypass -File `
#     D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\scripts\resume_deploy_noise.ps1
# Stop-Process any stale driver first. If all 36 done but no report, run
# analyze_deploy_noise.py manually. (scripts/ 2 levels under repo.)
# =====================================================================
$ErrorActionPreference = 'Stop'
$HERE = $PSScriptRoot
$REPO = Split-Path -Parent (Split-Path -Parent $HERE)
$LOG  = Join-Path $REPO "1-ModifiedMADDPGwithTDec\logs"
New-Item -ItemType Directory -Force $LOG | Out-Null
$boot = Join-Path $LOG "deploy_noise_driver.boot.log"
$p = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",(Join-Path $HERE "deploy_noise_driver.ps1")) `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $boot -RedirectStandardError ($boot + ".err")
Write-Output ("resume: deploy_noise_driver relaunched (idempotent; completed passes skipped)  pid=" + $p.Id)
