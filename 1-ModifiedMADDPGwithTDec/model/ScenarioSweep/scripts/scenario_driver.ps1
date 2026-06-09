# =====================================================================
# [RQ1-CMDP] SCENARIO SWEEP (resource-frontier supplement) — 96 ep600 runs.
#
# Varies ONLY the scenario (n_RB, n_veh); the locked CMDP config is FIXED
# (tau=8 eps=0.10 dual=pid kp=ki=1.0 kd=0.5 lam_max=20 episodes=600).
# Grid: n_RB in {2,3,4} x platoons in {4,5,6} (n_veh=4*platoons), EXCLUDING the
# nominal (rb3,pl5) cell which already exists. 8 cells x 4 arms x seeds {2,3,4}=96.
# Four arms per (cell,seed):
#   soft base        --mode soft                                   tag base_ep600_rb{R}_pl{P}
#   per-platoon PID  --mode hard --dual pid ... --lam_max 20       tag t8e10_pid_ep600_rb{R}_pl{P}
#   global_max       --mode hard --dual pid ... --lam_scope global_max  tag ..._glmax_rb{R}_pl{P}
#   fixed-w10        --mode soft --aoi_pen_type indicator --aoi_pen_w 10 tag qind_w10_ep600_rb{R}_pl{P}
#
# Detached, idempotent: a run is SKIPPED if its model dir's viol_rate.mat exists.
# PRIORITY: rb2 row first (rb2,pl6 / rb2,pl5 / rb2,pl4 = scarce/high-load frontier),
# then rb3, then rb4. Waves of <=6.
# ARCHIVED under model/ScenarioSweep/scripts/ (4 levels under repo) after the sweep
# finished. NOTE: Main.py still writes fresh runs to model/marl_model_<name> (its
# default out path); the completed run dirs were moved into model/ScenarioSweep/. So a
# re-run would emit to model/ and would need re-organizing; kept here for provenance.
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 600
$TAU = 8
$MAXCONC = 6
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 1440

# scripts/ is now 4 levels under repo: repo\1-ModifiedMADDPGwithTDec\model\ScenarioSweep\scripts
$REPO = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$MODEL= Join-Path $WD "model"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "scenario_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line; Add-Content -Path $DRIVERLOG -Value $line
}
function RunName($s) { "$($s.mode)_seed$($s.seed)_$($s.tag)" }
function Run-Done($s) {
    $vr = Join-Path $MODEL ("marl_model_" + (RunName $s) + "\viol_rate.mat")
    if (Test-Path $vr) { return $true }
    $f = Join-Path $LOG ((RunName $s) + ".out")
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}
function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"
    $a = @("-u","Main.py","--mode",$s.mode,"--tau","$TAU","--episodes","$EPISODES",
           "--seed","$($s.seed)","--n_RB","$($s.rb)","--n_veh","$($s.nveh)","--out_tag",$s.tag)
    $a += $s.extra
    $out = Join-Path $LOG "$name.out"; $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $a -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-44} pid={1}" -f $name, $p.Id)
}

# --- arm definitions (extra flags + tag stem) ---
$PIDFLAGS  = @("--eps","0.10","--dual","pid","--kp","1.0","--ki","1.0","--kd","0.5","--lam_max","20")
function ArmSpecs($rb,$pl,$seed) {
    $nveh = 4*$pl; $sfx = "_rb${rb}_pl${pl}"
    @(
      @{mode='soft'; seed=$seed; rb=$rb; nveh=$nveh; tag=("base_ep600"+$sfx);              extra=@()},
      @{mode='hard'; seed=$seed; rb=$rb; nveh=$nveh; tag=("t8e10_pid_ep600"+$sfx);         extra=$PIDFLAGS},
      @{mode='hard'; seed=$seed; rb=$rb; nveh=$nveh; tag=("t8e10_pid_ep600_glmax"+$sfx);   extra=($PIDFLAGS + @("--lam_scope","global_max"))},
      @{mode='soft'; seed=$seed; rb=$rb; nveh=$nveh; tag=("qind_w10_ep600"+$sfx);          extra=@("--aoi_pen_type","indicator","--aoi_pen_w","10")}
    )
}
# cells in PRIORITY order: rb2 row first, then rb3, then rb4 (skip nominal rb3/pl5)
$cells = @(@(2,6),@(2,5),@(2,4), @(3,4),@(3,6), @(4,4),@(4,5),@(4,6))
$specs = @()
foreach ($c in $cells) { foreach ($sd in 2,3,4) { $specs += ArmSpecs $c[0] $c[1] $sd } }

Say "================ SCENARIO SWEEP DRIVER START ================"
Say "cells=$($cells.Count) arms=4 seeds=3 -> $($specs.Count) runs; ep=$EPISODES tau=$TAU maxconc=$MAXCONC"
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
Say "================ SCENARIO SWEEP RUNS COMPLETE ================"

$SENT = Join-Path $LOG "scenario.finalized"
if (Test-Path $SENT) { Say "finalize sentinel present -> report already written; skipping" }
else {
    Say "running analyze_scenario.py -> RQ1_SCENARIO_SWEEP.md"
    & $PY (Join-Path $PSScriptRoot "analyze_scenario.py") 2>&1 | ForEach-Object { Say "  $_" }
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $SENT -Value (Get-Date).ToString('s'); Say "FINALIZE OK" }
    else { Say "FINALIZE returned $LASTEXITCODE (runs missing; report not written)" }
}
Say "================ SCENARIO SWEEP DRIVER EXIT ================"
