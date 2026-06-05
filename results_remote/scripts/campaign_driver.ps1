# =====================================================================
# [RQ1-CMDP] Self-contained, disconnect-proof campaign driver.
#
# Runs as ONE detached background process (Windows equivalent of a
# tmux-resident driver: tmux/screen are not installed on this host).
# It does NOT depend on the Claude Code agent staying connected.
#
# Sequence (concurrency = 6 per wave, ~6 runs at once on the GPU):
#   0. WAIT for Wave A (soft seeds 2-7) completion markers   <-- never relaunched
#   B. HARD t8e10  seeds 2..7                 (headline + metrics CIs)
#   C. HARD t8e15 + t10e10  seeds 2,3,4       (phase diagram)
#   D. HARD t10e15 + t12e10 seeds 2,3,4       (phase diagram)
#   E. HARD t12e15 s2,3,4 + FLOOR t8e10_floor s2,3,4 (phase + Exp2 safeguard)
# After each wave it BLOCKS on that wave's completion markers, then
# launches the next, so the GPU never holds more than ~6 training runs.
#
# Locked config (do NOT change): episodes=300, eta_lam=1.0, lam_max=20.
# A run is "done" when its .out log contains the savemat completion marker.
# Idempotent: a wave whose runs already have the marker is skipped instantly.
# =====================================================================
$ErrorActionPreference = 'Stop'
$EPISODES = 300
$ETA_LAM  = 1.0
$LAM_MAX  = 20.0
$POLL_SEC = 30
$WAVE_TIMEOUT_MIN = 300

$REPO = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PY   = Join-Path $REPO ".venv\Scripts\python.exe"
$WD   = Join-Path $REPO "1-ModifiedMADDPGwithTDec"
$LOG  = Join-Path $WD "logs"
$DRIVERLOG = Join-Path $LOG "campaign_driver.progress.log"
New-Item -ItemType Directory -Force $LOG | Out-Null
$MARKER = 'simulation took this much time'

function Say($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Output $line
    Add-Content -Path $DRIVERLOG -Value $line
}

function RunName($s) { "$($s.mode)_seed$($s.seed)_$($s.tag)" }

function Launch-Run($s) {
    $name = RunName $s
    $env:RQ1_CKPT_SUBDIR = "tmp/ddpg_$name"
    $argList = @("-u", "Main.py", "--mode", $s.mode, "--seed", "$($s.seed)",
                 "--episodes", "$EPISODES", "--tau", "$($s.tau)", "--eps", "$($s.eps)",
                 "--eta_lam", "$ETA_LAM", "--lam_max", "$LAM_MAX",
                 "--aoi_floor", "$($s.floor)", "--out_tag", $s.tag)
    $out = Join-Path $LOG "$name.out"
    $err = Join-Path $LOG "$name.err"
    $p = Start-Process -FilePath $PY -ArgumentList $argList -WorkingDirectory $WD `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Say ("  launched {0,-26} pid={1}" -f $name, $p.Id)
}

function Marker-Present($name) {
    $f = Join-Path $LOG "$name.out"
    return (Test-Path $f) -and (Select-String -Path $f -SimpleMatch $MARKER -Quiet)
}

function Wait-Markers($names, $label) {
    Say "WAIT  $label : need $($names.Count) markers"
    $deadline = (Get-Date).AddMinutes($WAVE_TIMEOUT_MIN)
    while ((Get-Date) -lt $deadline) {
        $done = @($names | Where-Object { Marker-Present $_ }).Count
        if ($done -eq $names.Count) { Say "READY $label : all $done done"; return $true }
        Start-Sleep -Seconds $POLL_SEC
    }
    Say "TIMEOUT $label (proceeding anyway)"; return $false
}

# Launch a wave only for runs not already complete, then wait for the whole set.
function Run-Wave($label, $specs) {
    $names = @($specs | ForEach-Object { RunName $_ })
    $todo  = @($specs | Where-Object { -not (Marker-Present (RunName $_)) })
    Say "WAVE $label : $($specs.Count) runs, $($todo.Count) to launch"
    foreach ($s in $todo) { Launch-Run $s }
    Wait-Markers $names $label | Out-Null
}

# ---------- wave definitions ----------
# NOTE: do NOT name these 'H'/'F' etc. -- 'h'/'H' is a built-in alias for
# Get-History and would shadow the function in command resolution.
function HardSpec($seed, $tau, $eps, $tag) { @{mode='hard'; seed=$seed; tau=$tau; eps=$eps; floor=0.0; tag=$tag} }
function FloorSpec($seed)                  { @{mode='hard'; seed=$seed; tau=8;   eps=0.10; floor=0.005; tag='t8e10_floor'} }

$waveA = @(2,3,4,5,6,7 | ForEach-Object { @{mode='soft'; seed=$_; tau=8; eps=0.10; floor=0.0; tag='base'} })
$waveB = @(2,3,4,5,6,7 | ForEach-Object { HardSpec $_ 8  0.10 't8e10' })
$waveC = @(2,3,4 | ForEach-Object { HardSpec $_ 8  0.15 't8e15' }) + @(2,3,4 | ForEach-Object { HardSpec $_ 10 0.10 't10e10' })
$waveD = @(2,3,4 | ForEach-Object { HardSpec $_ 10 0.15 't10e15' }) + @(2,3,4 | ForEach-Object { HardSpec $_ 12 0.10 't12e10' })
$waveE = @(2,3,4 | ForEach-Object { HardSpec $_ 12 0.15 't12e15' }) + @(2,3,4 | ForEach-Object { FloorSpec $_ })

Say "================ CAMPAIGN DRIVER START ================"
Say "repo=$REPO  episodes=$EPISODES eta_lam=$ETA_LAM lam_max=$LAM_MAX"

# Step 0: do NOT relaunch Wave A. Only wait for its markers.
$waveAnames = @($waveA | ForEach-Object { RunName $_ })
Wait-Markers $waveAnames "A (soft, pre-existing - NOT relaunched)" | Out-Null

Run-Wave "B (hard t8e10 seeds 2-7)"            $waveB
Run-Wave "C (hard t8e15 + t10e10 seeds 2,3,4)" $waveC
Run-Wave "D (hard t10e15 + t12e10 seeds 2,3,4)" $waveD
Run-Wave "E (hard t12e15 + FLOOR seeds 2,3,4)"  $waveE

Say "================ CAMPAIGN COMPLETE ================"
