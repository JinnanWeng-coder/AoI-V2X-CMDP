# =====================================================================
# [RQ1-CMDP] Claim-4 (PID damps the integral dual's limit-cycle) @ ep600 — SEED EXTENSION. 8 runs.
#
# WHY: the limit-cycle-damping evidence (claim 4) at the CANONICAL ep600 horizon currently
# has only n=6 (seeds 2-7, Canonical_ep600). The original 300-ep archived support was n=10
# (seeds 2-11, Legacy_300ep/claim4_support). At n=6 the Wilcoxon signed-rank floor is
# 2/2^6 = 0.031 (a 4/6 split is NOT significant). Extending the ep600 integral+PID arms to
# seeds 8,9,10,11 lifts ep600 to n=10 -> Wilcoxon floor 2/2^10 = 0.002, matching the archived
# evidence base on the SAME (8,10)/ep600/PID config the paper actually reports.
#
# This adds the 8 MISSING runs only (seeds 2-7 already exist in Canonical_ep600 and are reused
# by the analysis). NO Main.py change. Config byte-identical to ep600_driver.ps1:
#   hard, tau=8, eps=0.10, eta_lam=1.0, lam_max=20, aoi_floor=0.0, kp=ki=1.0 kd=0.5, ep600,
#   scenario 5 platoons x 4 veh x 3 RB, sigma const 0.3. The integral arm receives the (unused)
#   PID gains too, exactly as the canonical driver did, so the command line is identical.
#   B hard integral  tag t8e10_ep600       (--dual integral)
#   C hard pid        tag t8e10_pid_ep600   (--dual pid)
# Output -> model/Canonical_ep600/claim4_ext/  (run-dir NAMES are the canonical
#   marl_model_hard_seed{8..11}_t8e10[_pid]_ep600, which the analysis resolver finds by name
#   anywhere under model/ -- the subfolder is organizational only).
#
# Detached, idempotent (viol_rate.mat OR .out marker = done). Self-finalizes ->
# analyze_claim4_ep600.py (NUMBERS ONLY; operator cross-checks raw .mat + regenerates the
# manuscript figure locally).
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 600
$ETA_LAM = 1.0; $LAM_MAX = 20.0; $KP = 1.0; $KI = 1.0; $KD = 0.5
$MAXCONC = 8                 # 8 same-size runs; lower to 6 if the box is core-constrained
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 600

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$OUTDIR = Join-Path $WD "model\Canonical_ep600\claim4_ext"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "claim4_ep600_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line; Add-Content -Path $DRIVERLOG -Value $line
}
function RunName($s) { "hard_seed$($s.seed)_$($s.tag)" }
function Run-Done($s) {
    $vr = Join-Path $OUTDIR ("marl_model_" + (RunName $s) + "\viol_rate.mat")
    if (Test-Path $vr) { return $true }
    $f = Join-Path $LOG ((RunName $s) + ".out")
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}
function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"
    $argList = @("-u","Main.py","--mode","hard","--seed","$($s.seed)","--episodes","$EPISODES",
                 "--tau","8","--eps","0.10","--eta_lam","$ETA_LAM","--lam_max","$LAM_MAX","--aoi_floor","0.0",
                 "--dual",$s.dual,"--kp","$KP","--ki","$KI","--kd","$KD",
                 "--out_subdir","Canonical_ep600/claim4_ext","--out_tag",$s.tag)
    $out = Join-Path $LOG "$name.out"; $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-40} pid={1}" -f $name, $p.Id)
}

$specs = @()
foreach ($s in 8,9,10,11) { $specs += @{seed=$s; dual='integral'; tag='t8e10_ep600'} }
foreach ($s in 8,9,10,11) { $specs += @{seed=$s; dual='pid';      tag='t8e10_pid_ep600'} }

Say "================ CLAIM-4 EP600 SEED-EXT DRIVER START ================"
Say "specs=$($specs.Count) ep=$EPISODES seeds=8..11 arms=int+pid maxconc=$MAXCONC -> model\Canonical_ep600\claim4_ext\"
$todo = @($specs | Where-Object { -not (Run-Done $_) })
Say "to launch: $($todo.Count) (skipped already-complete: $($specs.Count - $todo.Count))"
$wave = 0
for ($i = 0; $i -lt $todo.Count; $i += $MAXCONC) {
    $wave++
    $chunk = $todo[$i..([Math]::Min($i+$MAXCONC-1, $todo.Count-1))]
    Say "WAVE $wave : launching $($chunk.Count) -> $(@($chunk | ForEach-Object { RunName $_ }) -join ', ')"
    foreach ($s in $chunk) { Launch-Run $s }
    $deadline = (Get-Date).AddMinutes($WAVE_TIMEOUT_MIN)
    while ((Get-Date) -lt $deadline) {
        $done = @($chunk | Where-Object { Run-Done $_ }).Count
        if ($done -eq $chunk.Count) { Say "READY wave$wave : all $done done"; break }
        Start-Sleep -Seconds $POLL_SEC
    }
}
Say "================ CLAIM-4 EP600 RUNS COMPLETE ================"

$SENT = Join-Path $LOG "claim4_ep600.finalized"
if (Test-Path $SENT) { Say "finalize sentinel present -> report already written; skipping" }
else {
    Say "running analyze_claim4_ep600.py -> RQ1_CLAIM4_EP600.md"
    & $PY (Join-Path $PSScriptRoot "analyze_claim4_ep600.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $SENT -Value (Get-Date).ToString('s'); Say "FINALIZE OK" }
    else { Say "FINALIZE returned $LASTEXITCODE (runs missing; report not written)" }
}
Say "================ CLAIM-4 EP600 DRIVER EXIT ================"
