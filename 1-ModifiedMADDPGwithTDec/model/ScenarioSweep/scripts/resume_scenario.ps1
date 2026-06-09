# =====================================================================
# [RQ1-CMDP] ONE-COMMAND idempotent reboot-resume for the scenario sweep.
# Relaunches the detached, self-finalizing scenario_driver.ps1 (skips runs whose
# viol_rate.mat exists; writes report once all 96 done unless sentinel set).
#   powershell -NoProfile -ExecutionPolicy Bypass -File `
#     D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\scripts\resume_scenario.ps1
# Stop-Process any stale driver polling dead runs first. If all 96 viol_rate.mat
# exist but no report (driver timeout exit), run analyze_scenario.py manually.
# (scripts/ is now 4 levels under repo: repo\1-ModifiedMADDPGwithTDec\model\ScenarioSweep\scripts.)
# =====================================================================
$ErrorActionPreference = 'Stop'
$HERE = $PSScriptRoot
$REPO = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $HERE)))
$LOG  = Join-Path $REPO "1-ModifiedMADDPGwithTDec\logs"
New-Item -ItemType Directory -Force $LOG | Out-Null
$boot = Join-Path $LOG "scenario_driver.boot.log"
$p = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",(Join-Path $HERE "scenario_driver.ps1")) `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $boot -RedirectStandardError ($boot + ".err")
Write-Output ("resume: scenario_driver relaunched (idempotent; completed runs skipped)  pid=" + $p.Id)
