# =====================================================================
# [RQ1-CMDP] WARM-start frozen-deployment eval (eval-only) — 12 runs, CHEAP path.
#
# All 12 deploy runs have usable checkpoints (tmp/ddpg_<name>, actor_0-4 + targets), so
# this loads each frozen policy and runs ONLY the deployment eval with the corrected WARM
# start (env.AoI=1 = steady-state). Writes *_test_warm*.mat INTO the existing
# model/ep600_deploy/marl_model_<name>/ dirs, alongside (never overwriting) the cold files.
#
# WARM is the default (--eval_start warm). NO training, NO dual, NO buffer -> minutes/run.
# Detached, idempotent: a run is DONE when viol_rate_test_warm_holdout_s14.mat exists.
# Waves of <=6. scripts/ is 2 levels under repo. Self-finalizes -> analyze_deploy_warm.py.
# =====================================================================
$ErrorActionPreference = 'Stop'
$TAU = 8
$MAXCONC = 6
$POLL_SEC = 20
$WAVE_TIMEOUT_MIN = 240

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$DEPLOY = Join-Path $WD "model\ep600_deploy"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "deploy_warm_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line; Add-Content -Path $DRIVERLOG -Value $line
}
function RunName($s) { "$($s.mode)_seed$($s.seed)_$($s.tag)" }
function Run-Done($s) {
    # eval-complete gate: the LAST warm eval-B file, else the end-of-run marker in .out
    $last = Join-Path $DEPLOY ("marl_model_" + (RunName $s) + "\viol_rate_test_warm_holdout_s14.mat")
    if (Test-Path $last) { return $true }
    $f = Join-Path $LOG ((RunName $s) + "_warm.out")
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}
function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"        # this run's frozen-policy checkpoints
    $a = @("-u","Main.py","--mode",$s.mode,"--tau","$TAU","--seed","$($s.seed)",
           "--eval_only","--eval_episodes","100","--eval_warmup","5",
           "--eval_holdout_seeds","12,13,14",
           "--out_subdir","ep600_deploy","--out_tag",$s.tag)
    $a += $s.extra
    $out = Join-Path $LOG "${name}_warm.out"; $err = Join-Path $LOG "${name}_warm.err"
    $p = Start-Process -FilePath $PY -ArgumentList $a -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-40} pid={1}  ckpt=tmp/ddpg_{0}" -f $name, $p.Id)
}

# --- arm definitions (eval-only: dual flags don't bite, follow the spec exactly) ---
$specs = @()
foreach ($sd in 2,3,4,5,6,7) {
    $specs += @{mode='soft'; seed=$sd; tag='base_ep600_deploy';      extra=@()}
    $specs += @{mode='hard'; seed=$sd; tag='t8e10_pid_ep600_deploy'; extra=@("--eps","0.10","--dual","pid")}
}

Say "================ DEPLOY WARM EVAL-ONLY DRIVER START ================"
Say "arms=2 seeds=6 -> $($specs.Count) eval-only runs; tau=$TAU maxconc=$MAXCONC warm-start; holdout 12,13,14"
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
Say "================ DEPLOY WARM RUNS COMPLETE ================"

$SENT = Join-Path $LOG "deploy_warm.finalized"
if (Test-Path $SENT) { Say "finalize sentinel present -> report already written; skipping" }
else {
    Say "running analyze_deploy_warm.py -> RQ1_DEPLOY_EVAL_WARM.md"
    & $PY (Join-Path $PSScriptRoot "analyze_deploy_warm.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $SENT -Value (Get-Date).ToString('s'); Say "FINALIZE OK" }
    else { Say "FINALIZE returned $LASTEXITCODE (runs missing; report not written)" }
}
Say "================ DEPLOY WARM DRIVER EXIT ================"
