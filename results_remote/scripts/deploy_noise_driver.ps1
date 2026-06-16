# =====================================================================
# [RQ1-CMDP] STOCHASTIC-policy deployment eval (eval-only) — 12 runs x 3 sigma = 36 passes.
#
# The decisive test: deploy the policy the CMDP actually certified — mu(s)+N(0,sigma),
# NOT its greedy determinization. eval-only on the existing ep600_deploy checkpoints
# (all 12 verified present); NO retraining. Sweep sigma in {0.05, 0.1, 0.3}; warm start
# (default, env.AoI=1). Writes *_test_warm_n{5,10,30}*.mat INTO the existing
# model/ep600_deploy/marl_model_<name>/ dirs, ALONGSIDE (never overwriting) the
# deterministic *_test_warm* and cold *_test* files.
#
# Detached, idempotent: a (run,sigma) is DONE when its viol_rate_test_warm_n<NN>_holdout_s14.mat
# exists. Waves of <=6. scripts/ is 2 levels under repo. Self-finalizes -> analyze_deploy_noise.py.
# =====================================================================
$ErrorActionPreference = 'Stop'
$TAU = 8
$MAXCONC = 6
$POLL_SEC = 20
$WAVE_TIMEOUT_MIN = 360

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$DEPLOY = Join-Path $WD "model\ep600_deploy"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "deploy_noise_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

# sigma -> file-suffix integer (round(sigma*100))
$SIGMAS = @(@{s=0.05; nn=5}, @{s=0.1; nn=10}, @{s=0.3; nn=30})

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line; Add-Content -Path $DRIVERLOG -Value $line
}
function RunTag($s) { "$($s.mode)_seed$($s.seed)_$($s.tag)_n$($s.nn)" }   # unique per (run,sigma)
function CkptName($s) { "$($s.mode)_seed$($s.seed)_$($s.tag)" }          # checkpoint is per-run (sigma-independent)
function Run-Done($s) {
    $last = Join-Path $DEPLOY ("marl_model_" + (CkptName $s) + "\viol_rate_test_warm_n$($s.nn)_holdout_s14.mat")
    if (Test-Path $last) { return $true }
    $f = Join-Path $LOG ((RunTag $s) + ".out")
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}
function Launch-Run($s) {
    $tag = RunTag $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$(CkptName $s)"    # this run's frozen-policy checkpoints
    $a = @("-u","Main.py","--mode",$s.mode,"--tau","$TAU","--seed","$($s.seed)",
           "--eval_only","--eval_episodes","100","--eval_warmup","5",
           "--eval_holdout_seeds","12,13,14","--eval_noise","$($s.sigma)",
           "--out_subdir","ep600_deploy","--out_tag",$s.tag)
    $a += $s.extra
    $out = Join-Path $LOG "${tag}.out"; $err = Join-Path $LOG "${tag}.err"
    $p = Start-Process -FilePath $PY -ArgumentList $a -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-48} pid={1}  sigma={2}" -f $tag, $p.Id, $s.sigma)
}

# --- build the 36 (run, sigma) specs ---
$specs = @()
foreach ($sd in 2,3,4,5,6,7) {
    foreach ($g in $SIGMAS) {
        $specs += @{mode='soft'; seed=$sd; tag='base_ep600_deploy';      sigma=$g.s; nn=$g.nn; extra=@()}
        $specs += @{mode='hard'; seed=$sd; tag='t8e10_pid_ep600_deploy'; sigma=$g.s; nn=$g.nn; extra=@("--eps","0.10","--dual","pid")}
    }
}

Say "================ DEPLOY NOISE EVAL-ONLY DRIVER START ================"
Say "12 runs x 3 sigma -> $($specs.Count) eval-only passes; tau=$TAU maxconc=$MAXCONC warm-start sigma in {0.05,0.1,0.3}"
$todo = @($specs | Where-Object { -not (Run-Done $_) })
Say "to launch: $($todo.Count) (skipped already-complete: $($specs.Count - $todo.Count))"
$wave = 0
for ($i = 0; $i -lt $todo.Count; $i += $MAXCONC) {
    $wave++
    $chunk = $todo[$i..([Math]::Min($i+$MAXCONC-1, $todo.Count-1))]
    Say "WAVE $wave : launching $($chunk.Count) -> $(@($chunk | ForEach-Object { RunTag $_ }) -join ', ')"
    foreach ($s in $chunk) { Launch-Run $s }
    $deadline = (Get-Date).AddMinutes($WAVE_TIMEOUT_MIN)
    while ((Get-Date) -lt $deadline) {
        $done = @($chunk | Where-Object { Run-Done $_ }).Count
        if ($done -eq $chunk.Count) { Say "READY wave$wave : all $done done"; break }
        Start-Sleep -Seconds $POLL_SEC
    }
}
Say "================ DEPLOY NOISE RUNS COMPLETE ================"

$SENT = Join-Path $LOG "deploy_noise.finalized"
if (Test-Path $SENT) { Say "finalize sentinel present -> report already written; skipping" }
else {
    Say "running analyze_deploy_noise.py -> RQ1_DEPLOY_EVAL_NOISE.md"
    & $PY (Join-Path $PSScriptRoot "analyze_deploy_noise.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $SENT -Value (Get-Date).ToString('s'); Say "FINALIZE OK" }
    else { Say "FINALIZE returned $LASTEXITCODE (runs missing; report not written)" }
}
Say "================ DEPLOY NOISE DRIVER EXIT ================"
