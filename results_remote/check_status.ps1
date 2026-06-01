# [RQ1-CMDP] Poll all run logs: show last episode reached + done flag + timing.
$WD  = Join-Path (Split-Path -Parent $PSScriptRoot) "1-ModifiedMADDPGwithTDec"
$LOG = Join-Path $WD "logs"
$now = Get-Date
Write-Output ("=== status @ {0:HH:mm:ss} ===" -f $now)
Get-ChildItem $LOG -Filter *.out -ErrorAction SilentlyContinue | Sort-Object Name | ForEach-Object {
    $name = $_.BaseName
    $txt  = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $txt) { Write-Output ("{0,-30} (empty)" -f $name); return }
    $eps = [regex]::Matches($txt, '\] ep (\d+)')
    $last = if ($eps.Count) { [int]$eps[$eps.Count-1].Groups[1].Value } else { -1 }
    $done = if ($txt -match 'simulation took this much time \.\.\.\s+([0-9.]+)') {
                "DONE ({0:N0}s)" -f [double]$Matches[1]
            } else { "running" }
    # crude per-ep estimate from file age if running
    Write-Output ("{0,-30} ep={1,4}  {2}" -f $name, $last, $done)
}
