# =====================================================================
# [RQ1-CMDP] Ablation A2 — epsilon-sensitivity sweep (the "knob -> level" demonstration). 12 runs.
#
# WHY: the locked constraint is P(AoI_j>tau)<=eps with eps=0.10. To show this is a genuine
# CONSTRAINT (a tunable target) and not a fixed penalty, sweep eps and check the achieved
# worst-platoon violation tracks eps (and that lambda_j relaxes as eps loosens). This is the
# POSITIVE counterpart to ablation #4 (fixed-weight penalty, the negative control).
#
# eps=0.10 ALREADY EXISTS (canonical PID arm, marl_model_hard_seed*_t8e10_pid_ep600) and is
# REUSED by the analysis -- so we only run the two NEW eps values:
#   eps=0.05  tag t8e5_pid_ep600
#   eps=0.20  tag t8e20_pid_ep600
# x seeds 2-7 = 12 runs. Config byte-identical to the canonical PID arm except --eps/--out_tag:
#   hard, tau=8, eta_lam=1.0, lam_max=20, aoi_floor=0.0, dual=pid kp=ki=1.0 kd=0.5, ep600,
#   scenario 5 platoons x 4 veh x 3 RB, sigma const 0.3. NO Main.py change (pure config).
# Output -> model/Ablations_ep600/eps_sweep/.
#
# Detached, idempotent (viol_rate.mat OR .out marker = done). Self-finalizes ->
# analyze_a2_eps.py (NUMBERS ONLY; operator cross-checks raw .mat + makes the figure locally).
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 600
$ETA_LAM = 1.0; $LAM_MAX = 20.0; $KP = 1.0; $KI = 1.0; $KD = 0.5
$MAXCONC = 6                 # 12 runs -> two even waves of 6 (REMOTE_RUNBOOK convention)
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 600

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$OUTDIR = Join-Path $WD "model\Ablations_ep600\eps_sweep"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "a2_eps_sweep_driver.progress.log"
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
                 "--tau","8","--eps","$($s.eps)","--eta_lam","$ETA_LAM","--lam_max","$LAM_MAX","--aoi_floor","0.0",
                 "--dual","pid","--kp","$KP","--ki","$KI","--kd","$KD",
                 "--out_subdir","Ablations_ep600/eps_sweep","--out_tag",$s.tag)
    $out = Join-Path $LOG "$name.out"; $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-40} pid={1}" -f $name, $p.Id)
}

$specs = @()
foreach ($s in 2,3,4,5,6,7) { $specs += @{seed=$s; eps='0.05'; tag='t8e5_pid_ep600'} }
foreach ($s in 2,3,4,5,6,7) { $specs += @{seed=$s; eps='0.20'; tag='t8e20_pid_ep600'} }

Say "================ A2 EPS-SWEEP DRIVER START ================"
Say "specs=$($specs.Count) ep=$EPISODES eps={0.05,0.20} (0.10 reused from canonical) maxconc=$MAXCONC -> model\Ablations_ep600\eps_sweep\"
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
Say "================ A2 EPS-SWEEP RUNS COMPLETE ================"

$SENT = Join-Path $LOG "a2_eps_sweep.finalized"
if (Test-Path $SENT) { Say "finalize sentinel present -> report already written; skipping" }
else {
    Say "running analyze_a2_eps.py -> RQ1_ABLATION_EPS_SWEEP.md"
    & $PY (Join-Path $PSScriptRoot "analyze_a2_eps.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $SENT -Value (Get-Date).ToString('s'); Say "FINALIZE OK" }
    else { Say "FINALIZE returned $LASTEXITCODE (runs missing; report not written)" }
}
Say "================ A2 EPS-SWEEP DRIVER EXIT ================"
