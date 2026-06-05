# [RQ1-CMDP] Block until every named run's .out log contains the completion marker.
# Usage: powershell -File wait_wave.ps1 -names soft_seed2_base,soft_seed3_base,...
param([string[]]$names, [int]$pollSec = 30, [int]$maxMin = 240)
$LOG = Join-Path (Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "1-ModifiedMADDPGwithTDec") "logs"
$marker = 'simulation took this much time'
$deadline = (Get-Date).AddMinutes($maxMin)
while ((Get-Date) -lt $deadline) {
    $done = 0
    foreach ($n in $names) {
        $f = Join-Path $LOG "$n.out"
        if ((Test-Path $f) -and (Select-String -Path $f -SimpleMatch $marker -Quiet)) { $done++ }
    }
    if ($done -eq $names.Count) {
        Write-Output ("ALL {0} DONE @ {1:HH:mm:ss}" -f $names.Count, (Get-Date)); exit 0
    }
    Start-Sleep -Seconds $pollSec
}
Write-Output "TIMEOUT waiting for wave"; exit 1
