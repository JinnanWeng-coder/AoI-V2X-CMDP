# =====================================================================
# [RQ1-CMDP] FROZEN-DEPLOYMENT eval (Experiments A in-dist / B held-out) — 12 runs.
#
# Re-train the 2 canonical arms into NEW *_deploy dirs (canonical _ep600 untouched),
# then append a frozen-policy eval (actor noise=0, no learning/dual/buffer; AoI reset +
# warmup discarded). LOCKED canonical config, canonical scenario (NO --n_RB/--n_veh):
#   tau=8 eps=0.10 dual=pid kp=ki=1.0 kd=0.5 lam_max=20 episodes=600, seeds 2-7.
#   Eval: 100 episodes, warmup 5, held-out seeds 12,13,14 (never used in training).
# 2 arms x seeds {2..7} = 12 train+eval runs.
#   soft base  --mode soft  ...                                tag base_ep600_deploy
#   per-pl PID --mode hard --dual pid ... --lam_max 20         tag t8e10_pid_ep600_deploy
#
# Detached, idempotent: a run is DONE only when its eval finished — gate on the LAST
# held-out file (viol_rate_test_holdout_s14.mat) OR the .out marker (printed AFTER eval).
# Waves of <=6. scripts/ is 2 levels under repo. Self-finalizes -> analyze_deploy.py.
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 600
$TAU = 8
$MAXCONC = 6
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 1440

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$MODEL= Join-Path $WD "model"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "deploy_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line; Add-Content -Path $DRIVERLOG -Value $line
}
function RunName($s) { "$($s.mode)_seed$($s.seed)_$($s.tag)" }
function Run-Done($s) {
    # eval-complete gate: the LAST eval-B file, else the end-of-run marker in .out
    $last = Join-Path $MODEL ("marl_model_" + (RunName $s) + "\viol_rate_test_holdout_s14.mat")
    if (Test-Path $last) { return $true }
    $f = Join-Path $LOG ((RunName $s) + ".out")
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}
function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"
    $a = @("-u","Main.py","--mode",$s.mode,"--tau","$TAU","--episodes","$EPISODES",
           "--seed","$($s.seed)","--out_tag",$s.tag,
           "--eval_episodes","100","--eval_warmup","5","--eval_holdout_seeds","12,13,14")
    $a += $s.extra
    $out = Join-Path $LOG "$name.out"; $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $a -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-40} pid={1}" -f $name, $p.Id)
}

# --- arm definitions (extra flags + tag) ---
$PIDFLAGS = @("--eps","0.10","--dual","pid","--kp","1.0","--ki","1.0","--kd","0.5","--lam_max","20")
$specs = @()
foreach ($sd in 2,3,4,5,6,7) {
    $specs += @{mode='soft'; seed=$sd; tag='base_ep600_deploy';      extra=@()}
    $specs += @{mode='hard'; seed=$sd; tag='t8e10_pid_ep600_deploy'; extra=$PIDFLAGS}
}

Say "================ DEPLOY EVAL DRIVER START ================"
Say "arms=2 seeds=6 -> $($specs.Count) runs; ep=$EPISODES tau=$TAU maxconc=$MAXCONC eval=100/warmup5/holdout12,13,14"
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
Say "================ DEPLOY EVAL RUNS COMPLETE ================"

$SENT = Join-Path $LOG "deploy.finalized"
if (Test-Path $SENT) { Say "finalize sentinel present -> report already written; skipping" }
else {
    Say "running analyze_deploy.py -> RQ1_DEPLOY_EVAL_AB.md"
    & $PY (Join-Path $PSScriptRoot "analyze_deploy.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $SENT -Value (Get-Date).ToString('s'); Say "FINALIZE OK" }
    else { Say "FINALIZE returned $LASTEXITCODE (runs missing; report not written)" }
}
Say "================ DEPLOY EVAL DRIVER EXIT ================"
