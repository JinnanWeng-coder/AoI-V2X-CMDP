# =====================================================================
# [RQ1-CMDP] ONE-COMMAND idempotent reboot-resume for the Task-2 study.
#
# Relaunches the detached driver (skips any run whose completion marker
# already exists -> only missing runs rerun from ep 0) AND the detached
# finalize-watcher (writes the report+figures once all 12 are done, unless
# the .finalized sentinel is already set). Both are hidden, orphaned
# Start-Process -> independent of this shell / your SSH. No git.
#
# Run after a host reboot that killed the run:
#   powershell -NoProfile -ExecutionPolicy Bypass -File `
#     D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\resume_stability.ps1
# =====================================================================
$ErrorActionPreference = 'Stop'
$HERE = $PSScriptRoot
$REPO = Split-Path -Parent (Split-Path -Parent $HERE)
$LOG  = Join-Path $REPO "1-ModifiedMADDPGwithTDec\logs"
New-Item -ItemType Directory -Force $LOG | Out-Null

function Launch-Detached($script, $bootname) {
    $boot = Join-Path $LOG $bootname
    $p = Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",$script) `
        -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $boot -RedirectStandardError ($boot + ".err")
    Write-Output ("launched {0}  pid={1}" -f (Split-Path -Leaf $script), $p.Id)
}

Launch-Detached (Join-Path $HERE "stability_driver.ps1")        "stability_driver.boot.log"
Launch-Detached (Join-Path $HERE "stability_finalize_watch.ps1") "stability_finalize_watch.boot.log"
Write-Output "resume: driver + finalize-watcher relaunched (idempotent; completed runs skipped)"
