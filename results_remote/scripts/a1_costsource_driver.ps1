# =====================================================================
# [RQ1-CMDP] Ablation A1 — cost-critic necessity (--cost_source raw, RCPO-style). 6 runs.
#
# Tests method component (c): the SEPARATE learned cost critic Q^c. The 'raw' arm prices the
# constraint off the raw episodic cost folded into the task-2 reward (RCPO-style), with NO
# separate Q^c in the actor objective; the per-episode dual update of lambda_j is UNCHANGED.
# Compare against the existing CRITIC arm = Canonical_ep600 hard PID (marl_model_hard_seed*_
# t8e10_pid_ep600), which the new code reproduces byte-identically under --cost_source critic
# (default). So we only need the 6 RAW runs.
#   raw worse / noisier  -> defends the separate cost critic (keep (c) in the method figure)
#   raw == critic        -> demote (c) to an inherited implementation detail
#
# Same locked config (tau=8 eps=0.10 PID kp=ki=1 kd=0.5 lam_max=20, ep600), seeds 2-7.
# Output -> model/Ablations_ep600/cost_source/. Detached, idempotent (viol_rate.mat = done).
# Self-finalizes -> analyze_a1_costsource.py (NUMBERS ONLY; operator cross-checks raw .mat).
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 600
$ETA_LAM = 1.0; $LAM_MAX = 20.0; $KP = 1.0; $KI = 1.0; $KD = 0.5
$MAXCONC = 6
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 600

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$OUTDIR = Join-Path $WD "model\Ablations_ep600\cost_source"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "a1_costsource_driver.progress.log"
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
                 "--dual","pid","--kp","$KP","--ki","$KI","--kd","$KD",
                 "--cost_source","raw",
                 "--out_subdir","Ablations_ep600/cost_source","--out_tag",$s.tag)
    $out = Join-Path $LOG "$name.out"; $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-40} pid={1}" -f $name, $p.Id)
}

$specs = @()
foreach ($s in 2,3,4,5,6,7) { $specs += @{seed=$s; tag='t8e10_pid_ep600_rawcost'} }

Say "================ A1 COST-SOURCE (raw/RCPO) DRIVER START ================"
Say "specs=$($specs.Count) ep=$EPISODES cost_source=raw maxconc=$MAXCONC -> model\Ablations_ep600\cost_source\"
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
Say "================ A1 RUNS COMPLETE ================"

$SENT = Join-Path $LOG "a1_costsource.finalized"
if (Test-Path $SENT) { Say "finalize sentinel present -> report already written; skipping" }
else {
    Say "running analyze_a1_costsource.py -> RQ1_ABLATION_COSTSOURCE.md"
    & $PY (Join-Path $PSScriptRoot "analyze_a1_costsource.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $SENT -Value (Get-Date).ToString('s'); Say "FINALIZE OK" }
    else { Say "FINALIZE returned $LASTEXITCODE (runs missing; report not written)" }
}
Say "================ A1 DRIVER EXIT ================"
