# =====================================================================
# [RQ1-CMDP #3] per-platoon vs GLOBAL multiplier ablation (control arm).
#
# Adds TWO control arms that replace per-platoon lambda_j with ONE global
# multiplier driven by (a) network-MEAN and (b) WORST per-platoon violation.
# The per-platoon arm (t8e10_pid_ep600) and soft baseline ALREADY EXIST -> NOT
# re-run here. 12 new runs = seeds {2..7} x {global_mean, global_max}.
#
# Config matches the existing per-platoon PID ep600 runs; ONLY --lam_scope and
# the --out_tag suffix change (exactly the task's RUN command; lam_max=20 and
# aoi_floor=0.0 come from defaults). Locked: mode=hard tau=8 eps=0.10 dual=pid
# kp=1 ki=1 kd=0.5 lam_max=20 episodes=600.
#
# Detached, idempotent: a run is SKIPPED if its model dir's viol_rate.mat already
# exists. Run dirs: marl_model_hard_seed<N>_t8e10_pid_ep600_glmean / _glmax.
# Concurrency <=6 (2 waves). After all 12 complete, runs analyze_ablation3.py.
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 600
$KP = 1.0; $KI = 1.0; $KD = 0.5
$MAXCONC = 6
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 1440

$REPO = Split-Path -Parent $PSScriptRoot
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$MODEL= Join-Path $WD "model"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "ablation3_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line; Add-Content -Path $DRIVERLOG -Value $line
}
function RunName($s) { "hard_seed$($s.seed)_$($s.tag)" }
# idempotency: done if the run's viol_rate.mat exists OR its .out has the marker
function Run-Done($s) {
    $vr = Join-Path $MODEL ("marl_model_" + (RunName $s) + "\viol_rate.mat")
    if (Test-Path $vr) { return $true }
    $f = Join-Path $LOG ((RunName $s) + ".out")
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}
function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"
    $argList = @("-u","Main.py","--mode","hard","--tau","8","--eps","0.10",
                 "--dual","pid","--kp","$KP","--ki","$KI","--kd","$KD",
                 "--episodes","$EPISODES","--seed","$($s.seed)",
                 "--lam_scope",$s.scope,"--out_tag",$s.tag)
    $out = Join-Path $LOG "$name.out"
    $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-36} pid={1}" -f $name, $p.Id)
}

$specs = @()
foreach ($sd in 2,3,4,5,6,7) { $specs += @{seed=$sd; scope='global_mean'; tag='t8e10_pid_ep600_glmean'} }
foreach ($sd in 2,3,4,5,6,7) { $specs += @{seed=$sd; scope='global_max';  tag='t8e10_pid_ep600_glmax'} }

Say "================ ABLATION#3 DRIVER START ================"
Say "ep=$EPISODES kp=$KP ki=$KI kd=$KD maxconc=$MAXCONC  (12 runs: 6 seeds x glmean/glmax)"
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
Say "================ ABLATION#3 RUNS COMPLETE ================"

$SENT = Join-Path $LOG "ablation3.finalized"
if (Test-Path $SENT) {
    Say "finalize sentinel present -> report already written; skipping"
} else {
    Say "running analyze_ablation3.py -> RQ1_ABLATION3_GLOBAL_LAMBDA.md"
    & $PY (Join-Path $PSScriptRoot "analyze_ablation3.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path $SENT -Value (Get-Date).ToString('s')
        Say "FINALIZE OK -> report written; sentinel set"
    } else {
        Say "FINALIZE returned $LASTEXITCODE (runs missing; report not written)"
    }
}
Say "================ ABLATION#3 DRIVER EXIT ================"
