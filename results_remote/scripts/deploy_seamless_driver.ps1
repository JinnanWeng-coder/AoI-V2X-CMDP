# =====================================================================
# [RQ1-CMDP] SEAMLESS deployment re-run (Deploy_seamless_800ep) — 12 runs.
#
# WHY: the existing frozen eval (--eval_only) RESTARTS the scenario from the seed's INITIAL
# geometry (Main.py ~L668), i.e. it tests the certified policy on a geometry ~30-45m displaced
# from where it was certified, AND it resets AoI=1. This batch removes BOTH confounds: train
# 600 ep exactly as canonical, then -- in the SAME process, on the SAME env (positions/AoI/
# channels carried over, vehicles keep driving via renew_positions every 20 ep) -- continue
# FROZEN (no learning/dual/buffer) for 200 episodes at the certified sigma=0.3, AoI NOT reset.
# Also dumps Scenario_Reconstruct.pkl at ep600 so a later batch can branch from the EXACT state
# (sigma-sweep / online-dual) via --seamless_resume. hard writes critic_loss_cost/cost_force.
#
# Acceptance gate (operator, local): the first-600-ep .mat (viol_rate / lambda / AoI_evolution)
# MUST match Canonical_ep600 within float tolerance -> confirms the tail/save code did not
# perturb training. 2 arms (soft base / per-platoon PID) x seeds 2-7 = 12 runs.
#
# Detached, idempotent (Start-Process; tmux/screen unavailable). A run is DONE when its
# viol_rate_seamless.mat exists (or its .out has the savemat completion marker). Waves of <=6.
# Self-finalizes -> analyze_seamless.py (NUMBERS ONLY; operator cross-checks raw .mat).
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 600
$TAIL = 200
$SIGMA = 0.3
$ETA_LAM = 1.0; $LAM_MAX = 20.0; $KP = 1.0; $KI = 1.0; $KD = 0.5
$MAXCONC = 6
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 600

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$OUTDIR = Join-Path $WD "model\Deploy_seamless_800ep"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "deploy_seamless_driver.progress.log"
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
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"     # this run's own checkpoint dir (concurrency-safe)
    if ($s.mode -eq 'soft') {
        $argList = @("-u","Main.py","--mode","soft","--seed","$($s.seed)","--episodes","$EPISODES",
                     "--seamless_tail","$TAIL","--seamless_noise","$SIGMA",
                     "--out_subdir","Deploy_seamless_800ep","--out_tag",$s.tag)
    } else {
        $argList = @("-u","Main.py","--mode","hard","--seed","$($s.seed)","--episodes","$EPISODES",
                     "--tau","8","--eps","0.10","--eta_lam","$ETA_LAM","--lam_max","$LAM_MAX","--aoi_floor","0.0",
                     "--dual","pid","--kp","$KP","--ki","$KI","--kd","$KD",
                     "--seamless_tail","$TAIL","--seamless_noise","$SIGMA",
                     "--out_subdir","Deploy_seamless_800ep","--out_tag",$s.tag)
    }
    $out = Join-Path $LOG "$name.out"; $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-40} pid={1}" -f $name, $p.Id)
}

function SSpec($seed){ @{mode='soft'; seed=$seed; tag='base_seamless800'} }
function HSpec($seed){ @{mode='hard'; seed=$seed; tag='t8e10_pid_seamless800'} }

$specs = @()
foreach ($s in 2,3,4,5,6,7) { $specs += (SSpec $s) }   # A soft base
foreach ($s in 2,3,4,5,6,7) { $specs += (HSpec $s) }   # B per-platoon PID

Say "================ DEPLOY SEAMLESS DRIVER START ================"
Say "specs=$($specs.Count) train_ep=$EPISODES tail=$TAIL sigma=$SIGMA maxconc=$MAXCONC -> model\Deploy_seamless_800ep\"
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
Say "================ DEPLOY SEAMLESS RUNS COMPLETE ================"

$SENT = Join-Path $LOG "deploy_seamless.finalized"
if (Test-Path $SENT) { Say "finalize sentinel present -> report already written; skipping" }
else {
    Say "running analyze_seamless.py -> RQ1_DEPLOY_SEAMLESS.md"
    & $PY (Join-Path $PSScriptRoot "analyze_seamless.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $SENT -Value (Get-Date).ToString('s'); Say "FINALIZE OK" }
    else { Say "FINALIZE returned $LASTEXITCODE (runs missing; report not written)" }
}
Say "================ DEPLOY SEAMLESS DRIVER EXIT ================"
