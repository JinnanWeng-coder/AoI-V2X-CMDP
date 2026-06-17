# =====================================================================
# [RQ1-CMDP] SEAMLESS ep1000 re-run (Deploy_seamless_1200ep) — 12 runs. (= idea 1)
#
# WHY: test the replay-buffer-eviction reading of the ep500-600 cost-critic-loss drop
# (memory_size=50000 = 500 ep; the buffer first fills at ep500 and then evicts the earliest,
# worst-policy transitions). Prediction: train 1000 ep with memory_size UNCHANGED -> the cost
# critic loss keeps dropping past ep600 then PLATEAUS once the 500-ep buffer is fully turned
# over (~ep1000), while reward_cost (per-episode violation) stays at the dual's eps setpoint
# (it must NOT drop below eps). Secondary: does the genuinely-hard seed (s2) worst platoon
# improve with more training (finding-5), shrinking the seamless deployment residual?
#
# IDENTICAL to deploy_seamless_driver.ps1 except --episodes 1000 and the output folder/tags.
# NO Main.py change: --seamless_tail/--seamless_noise already generalise. Same locked config
# (tau=8 eps=0.10 PID kp=ki=1 kd=0.5 lam_max=20, memory_size=50000 UNCHANGED). 2 arms
# (soft base / per-platoon PID) x seeds 2-7. Train 1000 ep then a frozen 200-ep tail at
# sigma=0.3 on the SAME env (AoI not reset) -> model\Deploy_seamless_1200ep\.
#
# Acceptance gate (operator, local): the first-600 episodes must reproduce Canonical_ep600 ---
# but AoI_evolution.mat is a rolling LAST-100-ep window (=ep900-999 here), so the gate compares
# viol_rate[:, :600] / lambda[:, :600] / AoI[:, :600] (analyze_seamless1000.py does this).
#
# Detached, idempotent. A run is DONE when its viol_rate_seamless.mat exists. Waves of <=6.
# Self-finalizes -> analyze_seamless1000.py (NUMBERS ONLY; operator cross-checks raw .mat).
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 1000
$TAIL = 200
$SIGMA = 0.3
$ETA_LAM = 1.0; $LAM_MAX = 20.0; $KP = 1.0; $KI = 1.0; $KD = 0.5
$MAXCONC = 6
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 900

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$OUTDIR = Join-Path $WD "model\Deploy_seamless_1200ep"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "deploy_seamless1000_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line; Add-Content -Path $DRIVERLOG -Value $line
}
function RunName($s) { "$($s.mode)_seed$($s.seed)_$($s.tag)" }
function Run-Done($s) {
    $vr = Join-Path $OUTDIR ("marl_model_" + (RunName $s) + "\viol_rate_seamless.mat")
    if (Test-Path $vr) { return $true }
    $f = Join-Path $LOG ((RunName $s) + ".out")
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}
function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"
    if ($s.mode -eq 'soft') {
        $argList = @("-u","Main.py","--mode","soft","--seed","$($s.seed)","--episodes","$EPISODES",
                     "--seamless_tail","$TAIL","--seamless_noise","$SIGMA",
                     "--out_subdir","Deploy_seamless_1200ep","--out_tag",$s.tag)
    } else {
        $argList = @("-u","Main.py","--mode","hard","--seed","$($s.seed)","--episodes","$EPISODES",
                     "--tau","8","--eps","0.10","--eta_lam","$ETA_LAM","--lam_max","$LAM_MAX","--aoi_floor","0.0",
                     "--dual","pid","--kp","$KP","--ki","$KI","--kd","$KD",
                     "--seamless_tail","$TAIL","--seamless_noise","$SIGMA",
                     "--out_subdir","Deploy_seamless_1200ep","--out_tag",$s.tag)
    }
    $out = Join-Path $LOG "$name.out"; $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-42} pid={1}" -f $name, $p.Id)
}

function SSpec($seed){ @{mode='soft'; seed=$seed; tag='base_seamless1200'} }
function HSpec($seed){ @{mode='hard'; seed=$seed; tag='t8e10_pid_seamless1200'} }

$specs = @()
foreach ($s in 2,3,4,5,6,7) { $specs += (SSpec $s) }   # A soft base
foreach ($s in 2,3,4,5,6,7) { $specs += (HSpec $s) }   # B per-platoon PID

Say "================ DEPLOY SEAMLESS-1000 DRIVER START ================"
Say "specs=$($specs.Count) train_ep=$EPISODES tail=$TAIL sigma=$SIGMA memory_size=UNCHANGED maxconc=$MAXCONC -> model\Deploy_seamless_1200ep\"
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
Say "================ DEPLOY SEAMLESS-1000 RUNS COMPLETE ================"

$SENT = Join-Path $LOG "deploy_seamless1000.finalized"
if (Test-Path $SENT) { Say "finalize sentinel present -> report already written; skipping" }
else {
    Say "running analyze_seamless1000.py -> RQ1_DEPLOY_SEAMLESS1000.md"
    & $PY (Join-Path $PSScriptRoot "analyze_seamless1000.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $SENT -Value (Get-Date).ToString('s'); Say "FINALIZE OK" }
    else { Say "FINALIZE returned $LASTEXITCODE (runs missing; report not written)" }
}
Say "================ DEPLOY SEAMLESS-1000 DRIVER EXIT ================"
