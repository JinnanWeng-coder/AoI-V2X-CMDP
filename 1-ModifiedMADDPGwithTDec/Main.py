import time
import numpy as np
import os
import argparse
import scipy.io
import Classes.Environment_Platoon as ENV
from local_critic import Agent
from global_critic import Global_Critic
from Classes.buffer import ReplayBuffer
import random
import pickle
import torch as T

try:
    from torch.utils.tensorboard import SummaryWriter
except ImportError:
    SummaryWriter = None

# ===================================================================== #
# [RQ1-CMDP] command-line configuration.
#   --mode soft : original Parvini-style soft AoI reward penalty (baseline)
#   --mode hard : per-platoon CMDP constraint P(AoI>tau)<=eps via a cost
#                 critic and a per-platoon Lagrange multiplier (proposed)
#   --smoke     : tiny run (few episodes/steps) for an end-to-end sanity test
# Full training on the remote machine, e.g.:
#   python Main.py --mode soft --episodes 500 --seed 2
#   python Main.py --mode hard --episodes 500 --seed 2
# ===================================================================== #
parser = argparse.ArgumentParser()
parser.add_argument('--mode', choices=['soft', 'hard'], default='soft')
# [RQ1-CMDP A1] cost-critic necessity ablation. In HARD mode, the constraint signal that enters
# the ACTOR objective is either: 'critic' (ours) = lambda_j * learned cost critic Q^c(s,pi(s));
# or 'raw' (RCPO-style) = fold -lambda_j*cost into the task-2 reward target and DROP the separate
# Q^c from the actor loss. The per-episode dual update of lambda_j is unchanged either way.
# Default 'critic' = byte-identical to the established runs.
parser.add_argument('--cost_source', choices=['critic', 'raw'], default='critic',
                    help='[RQ1-CMDP A1] hard-mode constraint signal: critic (learned Q^c, ours) vs raw (RCPO reward-folded)')
parser.add_argument('--episodes', type=int, default=500)
parser.add_argument('--seed', type=int, default=2)
parser.add_argument('--tau', type=float, default=8.0, help='AoI threshold (slots)')
parser.add_argument('--eps', type=float, default=0.10, help='target violation prob.')
parser.add_argument('--eta_lam', type=float, default=3.0, help='dual step size')
parser.add_argument('--lam_max', type=float, default=20.0, help='multiplier clip')
parser.add_argument('--smoke', action='store_true', help='tiny end-to-end test run')
# [RQ1-CMDP] feasibility safeguard: in hard mode keep a small AoI-penalty FLOOR
#   (aoi_penalty_coef = aoi_floor) so a structurally-unservable platoon still gets
#   gradient pressure once its lambda saturates, instead of being abandoned.
#   default 0.0 preserves the original hard-mode behaviour (penalty fully off).
parser.add_argument('--aoi_floor', type=float, default=0.0,
                    help='hard-mode soft AoI-penalty floor (0.0 = original behaviour)')
# [RQ1-CMDP] optional output-folder tag so runs that share (mode,seed) but differ
#   in tau/eps/floor do NOT overwrite each other's model/ outputs.
parser.add_argument('--out_tag', type=str, default='',
                    help='appended to the output folder label for run isolation')
# [RQ1-CMDP] STABILITY STUDY flags (both default to the EXISTING behaviour).
#   --sigma_anneal : linearly anneal the actor exploration noise from
#     --sigma_start (0.3) to --sigma_end (0.05) over training. Default OFF =>
#     noise stays the constant 0.3 set at agent construction (current behaviour).
#     Targets the per-seed RL-variance "hair-over-eps" miss (Year-1: sigma=0.3
#     actor noise was ~78% of reward variance).
#   --dual {integral,pid} : dual-ascent rule for lambda_j. 'integral' (default)
#     is the EXACT current pure-integral update (kept byte-for-byte so
#     --dual integral reproduces existing lambda traces). 'pid' is the
#     PID-Lagrangian of Stooke 2020 on the error e=(viol_rate_j - eps), with the
#     SAME [0, lam_max] clip; --kp/--ki/--kd are its gains. With kp=kd=0 and
#     ki=eta_lam the PID law reduces to the integral law. Targets the dual
#     limit-cycle/chatter.
parser.add_argument('--sigma_anneal', action='store_true',
                    help='[RQ1-CMDP] linearly anneal actor noise sigma_start->sigma_end over training (default off => const 0.3)')
parser.add_argument('--sigma_start', type=float, default=0.3, help='[RQ1-CMDP] anneal start sigma')
parser.add_argument('--sigma_end', type=float, default=0.05, help='[RQ1-CMDP] anneal end sigma')
parser.add_argument('--dual', choices=['integral', 'pid'], default='integral',
                    help='[RQ1-CMDP] dual update rule (default integral = current behaviour)')
parser.add_argument('--kp', type=float, default=1.0, help='[RQ1-CMDP] PID proportional gain')
parser.add_argument('--ki', type=float, default=1.0, help='[RQ1-CMDP] PID integral gain')
parser.add_argument('--kd', type=float, default=0.5, help='[RQ1-CMDP] PID derivative gain')
# [RQ1-CMDP #3] multiplier GRANULARITY ablation (control arm for the per-platoon claim).
#   per_platoon : each platoon j gets its own lambda_j driven by its own violation (ours).
#   global_mean : ONE shared lambda driven by the network-MEAN violation (replays the
#                 soft baseline's failure mode: average looks fine, worst platoon starves).
#   global_max  : ONE shared lambda driven by the WORST per-platoon violation (protects the
#                 worst but over-prices every platoon -> wastes power on the easy ones).
#   default 'per_platoon' is numerically IDENTICAL to the original update.
parser.add_argument('--lam_scope', choices=['per_platoon', 'global_mean', 'global_max'],
                    default='per_platoon',
                    help='[RQ1-CMDP #3] Lagrange-multiplier granularity (default per_platoon = current behaviour)')
# [RQ1-CMDP #4] soft-penalty SHAPE ablation (Qu-style fixed-weight threshold arm).
#   --aoi_pen_type raw       : original -AoI/20 penalty (default; byte-for-byte unchanged).
#   --aoi_pen_type indicator : fixed-weight threshold penalty -aoi_pen_w*1{AoI>tau} -- same
#     threshold signal as the hard constraint, but a FIXED weight and NO dual. Use with
#     --mode soft to get the "penalty, not constraint" control arm.
parser.add_argument('--aoi_pen_type', choices=['raw', 'indicator'], default='raw',
                    help='[RQ1-CMDP #4] soft AoI penalty shape (default raw = current behaviour)')
parser.add_argument('--aoi_pen_w', type=float, default=5.0,
                    help='[RQ1-CMDP #4] fixed weight for the indicator penalty (only used when aoi_pen_type=indicator)')
# [RQ1-CMDP scenario sweep] resource pool / fleet size (defaults = original scenario).
#   n_RB = shared resource blocks; n_veh = total vehicles (platoons = n_veh/size_platoon).
#   Everything downstream (n_platoon, n_input via get_state, network dims, .mat shapes)
#   auto-sizes; the locked CMDP config (tau/eps/PID/lam_max) is unchanged.
parser.add_argument('--n_RB', type=int, default=3, help='[RQ1-CMDP] number of resource blocks (scenario sweep)')
parser.add_argument('--n_veh', type=int, default=20, help='[RQ1-CMDP] total vehicles; platoons = n_veh/size_platoon (scenario sweep)')
# [RQ1-CMDP] frozen-deployment evaluation (Experiments A in-distribution / B held-out).
#   Default 0 = no eval (training path byte-for-byte unchanged).
parser.add_argument('--eval_episodes', type=int, default=0,
                    help='[RQ1-CMDP] after training, run N frozen-deployment eval episodes (noise OFF, no learning/dual/buffer); 0=off')
parser.add_argument('--eval_warmup', type=int, default=5,
                    help='[RQ1-CMDP] eval episodes discarded as warmup (env.AoI reset at eval start per --eval_start)')
parser.add_argument('--eval_holdout_seeds', type=str, default='',
                    help='[RQ1-CMDP] comma-separated held-out seeds for Experiment B (fresh new_random_game per seed); empty=A only')
# [RQ1-CMDP] eval start state + eval-only mode + output subfolder.
#   --eval_start warm (DEFAULT): AoI starts at 1 slot (steady-state deployment); files get
#     a _warm suffix (*_test_warm*.mat) so the committed cold-boot results are never
#     overwritten. cold: legacy synchronized cold boot at AoI=100 (plain *_test*.mat) —
#     known to deadlock the greedy frozen policy (documented robustness caveat).
#   --eval_only: skip training entirely; load this run's checkpoints (env var
#     RQ1_CKPT_SUBDIR must point at the run's checkpoint subdir) and run only the eval.
#   --out_subdir: optional subfolder under model/ (e.g. ep600_deploy) for run isolation.
parser.add_argument('--eval_start', choices=['warm', 'cold'], default='warm',
                    help='[RQ1-CMDP] eval initial AoI: warm=1 (steady state, _warm files), cold=100 (legacy names)')
parser.add_argument('--eval_only', action='store_true',
                    help='[RQ1-CMDP] skip training; load checkpoints (RQ1_CKPT_SUBDIR) and run only the frozen eval')
parser.add_argument('--out_subdir', type=str, default='',
                    help='[RQ1-CMDP] optional subfolder under model/ for all outputs (e.g. ep600_deploy)')
# [RQ1-CMDP] eval-time exploration noise: 0.0 (default) = deterministic greedy deployment;
#   >0 deploys the STOCHASTIC policy mu(s)+N(0,sigma) — the policy the CMDP actually certified
#   during training (sigma=0.3). Files get a _n{sigma*100} suffix so they NEVER overwrite the
#   deterministic (greedy) results.
parser.add_argument('--eval_noise', type=float, default=0.0,
                    help='[RQ1-CMDP] actor exploration sigma DURING eval (0=greedy; e.g. 0.3 = certified stochastic policy)')
# [RQ1-CMDP] SEAMLESS frozen-deployment tail (Deploy_seamless_800ep study). After the normal
#   training loop, KEEP the SAME env (positions / AoI / channels carried over from the end of
#   training) and continue the renew_positions-every-20-ep drive for N more episodes, but FREEZE
#   the policy (no learning, no dual, no buffer). AoI is NOT reset -> a true seamless continuation
#   on the geometry the policy was CERTIFIED on (unlike --eval_only which restarts from the seed's
#   initial geometry, Main.py ~L668). Default 0 = off (training path byte-for-byte unchanged).
#   At ep_offset it also dumps Scenario_Reconstruct.pkl (full env + RNG + dual state) so a later
#   batch can branch from the exact ep600 state (sigma-sweep / online-dual) via --seamless_resume.
parser.add_argument('--seamless_tail', type=int, default=0,
                    help='[RQ1-CMDP] frozen continuation episodes after training (same env, no AoI reset, no learning/dual/buffer); 0=off')
parser.add_argument('--seamless_noise', type=float, default=0.3,
                    help='[RQ1-CMDP] actor sigma during the seamless tail (default 0.3 = the certified stochastic policy)')
parser.add_argument('--seamless_resume', type=str, default='',
                    help='[RQ1-CMDP] path to a Scenario_Reconstruct.pkl: restore env+RNG+dual, load checkpoints, run a frozen tail from the saved ep_offset (no training). Writes *_seamless_n{NN}.mat')
args = parser.parse_args()

CONSTRAINT_MODE = args.mode
SEED = args.seed
random.seed(SEED)
np.random.seed(SEED)
T.manual_seed(SEED)
T.cuda.manual_seed_all(SEED)     # safe even if no GPU
# Optional, for stricter determinism on GPU (slower):
#T.backends.cudnn.deterministic = True
#T.backends.cudnn.benchmark = False

'''
---------------------------------------------------------------------------------------
Simulation code of the paper:
    "AoI-Aware Resource Allocation for Platoon-Based C-V2X Networks via Multi-Agent 
                        Multi-Task Reinforcement Learning"

Written by  : Mohammad Parvini, M.Sc. student at Tarbiat Modares University.
---------------------------------------------------------------------------------------
---> We have built our simulation following the urban case defined in Annex A of 
     3GPP, TS 36.885, "Study on LTE-based V2X Services".
---------------------------------------------------------------------------------------
'''

start = time.time()
# ################## SETTINGS ######################
up_lanes = [i / 2.0 for i in
            [3.5 / 2, 3.5 / 2 + 3.5, 250 + 3.5 / 2, 250 + 3.5 + 3.5 / 2, 500 + 3.5 / 2, 500 + 3.5 + 3.5 / 2]]
down_lanes = [i / 2.0 for i in
              [250 - 3.5 - 3.5 / 2, 250 - 3.5 / 2, 500 - 3.5 - 3.5 / 2, 500 - 3.5 / 2, 750 - 3.5 - 3.5 / 2,
               750 - 3.5 / 2]]
left_lanes = [i / 2.0 for i in
              [3.5 / 2, 3.5 / 2 + 3.5, 433 + 3.5 / 2, 433 + 3.5 + 3.5 / 2, 866 + 3.5 / 2, 866 + 3.5 + 3.5 / 2]]
right_lanes = [i / 2.0 for i in
               [433 - 3.5 - 3.5 / 2, 433 - 3.5 / 2, 866 - 3.5 - 3.5 / 2, 866 - 3.5 / 2, 1299 - 3.5 - 3.5 / 2,
                1299 - 3.5 / 2]]
print('------------- lanes are -------------')
print('up_lanes :', up_lanes)
print('down_lanes :', down_lanes)
print('left_lanes :', left_lanes)
print('right_lanes :', right_lanes)
print('------------------------------------')
width = 750 / 2
height = 1298 / 2
IS_TRAIN = 0 if (args.eval_only or args.seamless_resume) else 1   # [RQ1-CMDP] --eval_only / --seamless_resume skip training
IS_TEST = 1 - IS_TRAIN
label = 'marl_model_' + CONSTRAINT_MODE + '_seed' + str(SEED)   # [RQ1-CMDP] separate soft/hard/seed outputs
if args.out_tag:                                               # [RQ1-CMDP] further isolate by tau/eps/floor
    label = label + '_' + args.out_tag
if args.out_subdir:                                            # [RQ1-CMDP] optional model/ subfolder
    label = args.out_subdir + '/' + label

current_dir = os.path.dirname(os.path.realpath(__file__))
repo_dir = os.path.dirname(current_dir)
algo_name = os.path.basename(current_dir)
if SummaryWriter is not None:
    tensorboard_log_dir = os.path.join(current_dir, "runs", "TensorBoardLog")
    writer = SummaryWriter(log_dir=tensorboard_log_dir, purge_step=0)
    print("TensorBoard log dir:", tensorboard_log_dir)
else:
    writer = None
    print("TensorBoard is disabled. Install it with: pip install tensorboard")
# ------------------------------------------------------------------------------------------------------------------ #
# simulation parameters:
# ------------------------------------------------------------------------------------------------------------------ #
# ------------------------------------------------------------------------------------------------------------------ #
size_platoon = 4
n_veh = args.n_veh  # [RQ1-CMDP] total vehicles (scenario sweep; default 20)
n_platoon = int(n_veh / size_platoon)  # number of platoons
n_RB = args.n_RB  # [RQ1-CMDP] resource blocks (scenario sweep; default 3)
n_S = 2  # decision parameter for Intra/Inter platoon communication
Gap = 25 # meter
max_power = 30  # platoon leader maximum power in dbm ---> watt = 10^[(dbm - 30)/10]
V2I_min = 540   # minimum required data rate for V2I Communication = 3bps/Hz --> 3 * B.W * time_fast = 540
bandwidth = int(180000)
V2V_size = int((4000) * 8) # CAM message size
# ------------------------------------------------------------------------------------------------------------------ #
# ------------------------------------------------------------------------------------------------------------------ #
## Initializations ##
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# ------- characteristics related to the network -------- #
batch_size = 64
memory_size = 50000
gamma = 0.99
alpha = 0.0001
beta = 0.001
update_actor_interval = 2 # d in the paper, delay the policy update by d
noise = 0.3
# actor and critic hidden layers
C_fc1_dims = 1024
C_fc2_dims = 512
C_fc3_dims = 256

l_c1_dims = 512
l_c2_dims = 256

A_fc1_dims = 1024
A_fc2_dims = 512
# ------------------------------

tau = 0.005
env = ENV.Environ(down_lanes, up_lanes, left_lanes, right_lanes, width, height, n_veh, size_platoon, n_RB,
                  V2I_min, bandwidth, V2V_size, Gap)
env.new_random_game()  # initialize parameters in env

# [RQ1-CMDP] configure the constraint on the environment.
env.constraint_mode = CONSTRAINT_MODE
env.tau_aoi = args.tau
env.eps_viol = args.eps
# In 'hard' mode AoI is a constraint, so the soft reward penalty is switched off;
# in 'soft' mode it keeps the original 1/20 weight.
env.aoi_penalty_coef = args.aoi_floor if CONSTRAINT_MODE == 'hard' else (1.0 / 20)
env.aoi_pen_type = args.aoi_pen_type        # [RQ1-CMDP #4] soft-penalty shape
env.aoi_pen_w = args.aoi_pen_w              # [RQ1-CMDP #4] fixed indicator weight

n_episode = args.episodes
n_step_per_episode = int(env.time_slow / env.time_fast)
n_episode_test = 100  # test episodes
if args.smoke:                       # tiny end-to-end sanity run
    n_episode = 3
    n_step_per_episode = 20
    n_episode_test = 3
print('=== RQ1 run: mode=%s seed=%d episodes=%d tau=%.1f eps=%.2f eta_lam=%.2f '
      'aoi_floor=%.4f label=%s smoke=%s ==='
      % (CONSTRAINT_MODE, SEED, n_episode, args.tau, args.eps, args.eta_lam,
         args.aoi_floor, label, args.smoke))
# [RQ1-CMDP] stability-study banner.
if args.sigma_anneal:
    print('    [stability] sigma-anneal ON: %.3f -> %.3f linearly over %d episodes'
          % (args.sigma_start, args.sigma_end, n_episode))
else:
    print('    [stability] sigma-anneal OFF: noise const = %.3f' % noise)
if args.dual == 'pid':
    print('    [stability] dual=PID-Lagrangian (kp=%.2f ki=%.2f kd=%.2f), clip[0,%.1f]'
          % (args.kp, args.ki, args.kd, args.lam_max))
else:
    print('    [stability] dual=integral (eta_lam=%.2f), clip[0,%.1f]'
          % (args.eta_lam, args.lam_max))
# ------------------------------------------------------------------------------------------------------------------ #
def get_state(env, idx):
    """ Get state from the environment """

    V2I_abs = (env.V2I_channels_abs[idx * size_platoon] - 60) / 60.0

    V2V_abs = (env.V2V_channels_abs[idx * size_platoon, idx * size_platoon + (1 + np.arange(size_platoon - 1))] - 60)/60.0

    V2I_fast = (env.V2I_channels_with_fastfading[idx * size_platoon, :] - env.V2I_channels_abs[
        idx * size_platoon] + 10) / 35

    V2V_fast = (env.V2V_channels_with_fastfading[idx * size_platoon, idx * size_platoon + (1 + np.arange(size_platoon - 1)), :]
                - env.V2V_channels_abs[idx * size_platoon, idx * size_platoon +
                                       (1 + np.arange(size_platoon - 1))].reshape(size_platoon - 1, 1) + 10) / 35

    Interference = (env.Interference_all[idx] + 60) / 60

    AoI_levels = env.AoI[idx] / (int(env.time_slow / env.time_fast))

    V2V_load_remaining = np.asarray([env.V2V_demand[idx] / env.V2V_demand_size])

    # time_remaining = np.asarray([env.individual_time_limit[idx] / env.time_slow])

    return np.concatenate((np.reshape(V2I_abs, -1), np.reshape(V2I_fast, -1), np.reshape(V2V_abs, -1),
                           np.reshape(V2V_fast, -1), np.reshape(Interference, -1), np.reshape(AoI_levels, -1), V2V_load_remaining), axis=0)
# ------------------------------------------------------------------------------------------------------------------ #
# ------------------------------------------------------------------------------------------------------------------ #
n_input = len(get_state(env=env, idx=0))
n_output = 3  # number of actions ---> channel selection, mode selection, power
# --------------------------------------------------------------
agents = []
for index_agent in range(n_platoon):
    print("Initializing agent", index_agent+1)
    agent = Agent(alpha, beta, n_input, tau, n_output, gamma, l_c1_dims, l_c2_dims,
                  A_fc1_dims, A_fc2_dims, batch_size, n_platoon, index_agent, noise)
    agent.constraint_mode = CONSTRAINT_MODE     # [RQ1-CMDP]
    agent.cost_source = args.cost_source        # [RQ1-CMDP A1] 'critic' (ours) vs 'raw' (RCPO)
    agent.lam = 0.0                             # per-platoon multiplier lambda_j
    agents.append(agent)
memory = ReplayBuffer(memory_size, n_input, n_output, n_platoon)
print("Initializing Global critic ...")
global_agent = Global_Critic(beta, n_input, tau, n_output, gamma, C_fc1_dims, C_fc2_dims, C_fc3_dims,
                 batch_size, n_platoon, update_actor_interval, noise)
# ------------------------------------------------------------------------------------------------------------------ #
# ------------------------------------------------------------------------------------------------------------------ #
AoI_evolution = np.zeros([n_platoon, n_episode_test, n_step_per_episode], dtype=np.float16)
Demand_total = np.zeros([n_platoon, n_episode_test, n_step_per_episode], dtype=np.float16)
V2I_total = np.zeros([n_platoon, n_episode_test, n_step_per_episode], dtype=np.float16)
V2V_total = np.zeros([n_platoon, n_episode_test, n_step_per_episode], dtype=np.float16)
power_total = np.zeros([n_platoon, n_episode_test, n_step_per_episode], dtype=np.float16)

AoI_total = np.zeros([n_platoon, n_episode], dtype=np.float16)
record_reward_t1_ = np.zeros([n_platoon, n_episode], dtype=np.float16)
record_reward_t2_ = np.zeros([n_platoon, n_episode], dtype=np.float16)
record_reward_cost_ = np.zeros([n_platoon, n_episode], dtype=np.float16)   # [RQ1-CMDP] cost-critic reward = mean 1{AoI>tau} (== per-episode violation rate)
record_reward_total_ = np.zeros([n_platoon, n_episode], dtype=np.float16)  # [RQ1-CMDP] per-platoon total task reward = t1 + t2
record_reward_global_ = np.zeros([n_episode], dtype=np.float16)
Jain_total = np.zeros([n_episode], dtype=np.float16)
# [RQ1-CMDP] per-platoon, per-episode violation rate and multiplier traces.
# These two are the headline RQ1 outputs (soft vs hard comparison).
viol_total = np.zeros([n_platoon, n_episode], dtype=np.float32)
lambda_total = np.zeros([n_platoon, n_episode], dtype=np.float32)
# [RQ1-CMDP] cost-critic training diagnostics (pure logging, from local_critic diag_*):
#   critic_loss_cost = per-episode mean Bellman MSE of Q^c (is the cost critic converging?)
#   cost_force       = per-episode mean of lam_j * mean Q^c(s, pi(s)) (the constraint force)
critic_loss_cost_total = np.zeros([n_platoon, n_episode], dtype=np.float32)
cost_force_total = np.zeros([n_platoon, n_episode], dtype=np.float32)


# [RQ1-CMDP] frozen-deployment evaluation (Experiment A in-distribution / B held-out).
#   Freeze the trained actor: noise=0 (deterministic policy), NO learning, NO dual update,
#   NO buffer writes. Same per-step env stepping as training (choose_action ->
#   act_for_training -> renew fastfading -> Compute_Interference -> get_state). Records
#   per-step platoon AoI + Tx power; discards the first `warmup` episodes (AoI reset to 100
#   at eval start). reseed=None -> in-distribution (continue the training RNG stream);
#   reseed=int -> a held-out scenario (fresh seed + env.new_random_game()). Reads nothing,
#   writes nothing into the training arrays/.mat.
def run_frozen_eval(n_eval, warmup, reseed=None):
    if reseed is not None:
        random.seed(reseed)
        np.random.seed(reseed)
        T.manual_seed(reseed)
        env.new_random_game()
    for ag in agents:
        ag.noise = args.eval_noise                      # 0 = deterministic greedy; >0 = certified stochastic policy
    total = int(n_eval + warmup)
    aoi_evo = np.zeros([n_platoon, total, n_step_per_episode], dtype=np.float16)
    pow_evo = np.zeros([n_platoon, total, n_step_per_episode], dtype=np.float16)
    # [RQ1-CMDP] warm (default) = steady-state deployment: AoI starts at 1 slot
    # (just-served); cold = legacy synchronized cold boot at the AoI cap (100) — known
    # to deadlock the greedy frozen policy (kept reproducible as the documented caveat).
    start_aoi = 1.0 if args.eval_start == 'warm' else 100.0
    env.AoI = np.ones(int(n_platoon)) * start_aoi
    for ep in range(total):
        env.V2V_demand = env.V2V_demand_size * np.ones(n_platoon, dtype=np.float16)
        env.individual_time_limit = env.time_slow * np.ones(n_platoon, dtype=np.float16)
        env.active_links = np.ones((int(env.n_Veh / env.size_platoon)), dtype='bool')
        if ep % 20 == 0:
            env.renew_positions()
            env.renew_channel(n_veh, size_platoon)
            env.renew_channels_fastfading()
        state_old = [get_state(env=env, idx=i) for i in range(n_platoon)]
        for i_step in range(n_step_per_episode):
            at = np.zeros([n_platoon, n_output], dtype=int)
            for i in range(n_platoon):
                a = np.clip(agents[i].choose_action(state_old[i]), -0.999, 0.999)
                at[i, 0] = ((a[0] + 1) / 2) * n_RB
                at[i, 1] = ((a[1] + 1) / 2) * n_S
                at[i, 2] = np.round(np.clip(((a[2] + 1) / 2) * max_power, 1, max_power))
            _, _, _, _, platoon_AoI, C_rate, V_rate, Demand_R, V2V_success = env.act_for_training(at.copy())
            env.renew_channels_fastfading()
            env.Compute_Interference(at.copy())
            for i in range(n_platoon):
                aoi_evo[i, ep, i_step] = platoon_AoI[i]
                pow_evo[i, ep, i_step] = at[i, 2]
            state_old = [get_state(env=env, idx=i) for i in range(n_platoon)]
    return aoi_evo[:, warmup:, :], pow_evo[:, warmup:, :]


# [RQ1-CMDP] full deployment-eval suite (A in-distribution + B held-out), shared by the
# post-training path and --eval_only. File naming: warm start (default) writes
# *_test_warm*.mat; cold start keeps the legacy *_test*.mat names, so the committed
# cold-boot results are never overwritten.
def run_deploy_eval_suite():
    sfx = '_warm' if args.eval_start == 'warm' else ''
    if args.eval_noise > 0:
        sfx = sfx + ('_n%d' % round(args.eval_noise * 100))   # e.g. _warm_n30 for sigma=0.3
    ed = os.path.join(current_dir, "model", label)
    os.makedirs(ed, exist_ok=True)
    print('=== [RQ1-CMDP] frozen-deployment eval A (in-distribution, %s start) ===' % args.eval_start)
    aoi_te, pow_te = run_frozen_eval(args.eval_episodes, args.eval_warmup, reseed=None)
    viol_te = (aoi_te > env.tau_aoi).mean(axis=(1, 2))
    scipy.io.savemat(os.path.join(ed, 'AoI_evolution_test%s.mat' % sfx), {'AoI_evolution_test': aoi_te})
    scipy.io.savemat(os.path.join(ed, 'power_test%s.mat' % sfx), {'power_test': pow_te})
    scipy.io.savemat(os.path.join(ed, 'viol_rate_test%s.mat' % sfx), {'viol_rate_test': viol_te})
    print('  eval A%s: worst-platoon viol = %.3f  net-mean = %.3f  mean power = %.2f'
          % (sfx, float(viol_te.max()), float(viol_te.mean()), float(pow_te.mean())))
    for x in args.eval_holdout_seeds.split(','):
        x = x.strip()
        if x == '':
            continue
        hs = int(x)
        print('=== [RQ1-CMDP] frozen-deployment eval B (held-out seed %d, %s start) ===' % (hs, args.eval_start))
        aoi_h, pow_h = run_frozen_eval(args.eval_episodes, args.eval_warmup, reseed=hs)
        viol_h = (aoi_h > env.tau_aoi).mean(axis=(1, 2))
        scipy.io.savemat(os.path.join(ed, 'AoI_evolution_test%s_holdout_s%d.mat' % (sfx, hs)), {'AoI_evolution_test': aoi_h})
        scipy.io.savemat(os.path.join(ed, 'power_test%s_holdout_s%d.mat' % (sfx, hs)), {'power_test': pow_h})
        scipy.io.savemat(os.path.join(ed, 'viol_rate_test%s_holdout_s%d.mat' % (sfx, hs)), {'viol_rate_test': viol_h})
        print('  eval B%s(s%d): worst-platoon viol = %.3f  net-mean = %.3f  mean power = %.2f'
              % (sfx, hs, float(viol_h.max()), float(viol_h.mean()), float(pow_h.mean())))


# [RQ1-CMDP] SEAMLESS frozen continuation tail. Keep the CURRENT env (do NOT reseed, do NOT
#   new_random_game, do NOT reset AoI): the policy continues on the very geometry it was
#   certified on, vehicles keep driving (renew_positions every 20 ep). FREEZE the policy: no
#   buffer writes, no global_learn, no dual update. ep_offset keeps the every-20 renew cadence
#   in phase with training (trained ep 0..N-1 -> tail ep N.. ). The per-step env stepping mirrors
#   run_frozen_eval / the training loop EXACTLY (only learning removed).
def run_seamless_tail(n_tail, ep_offset, noise):
    for ag in agents:
        ag.noise = noise
    aoi_evo = np.zeros([n_platoon, n_tail, n_step_per_episode], dtype=np.float16)
    pow_evo = np.zeros([n_platoon, n_tail, n_step_per_episode], dtype=np.float16)
    for t in range(n_tail):
        ep = ep_offset + t
        env.V2V_demand = env.V2V_demand_size * np.ones(n_platoon, dtype=np.float16)
        env.individual_time_limit = env.time_slow * np.ones(n_platoon, dtype=np.float16)
        env.active_links = np.ones((int(env.n_Veh / env.size_platoon)), dtype='bool')
        if ep % 20 == 0:
            env.renew_positions()
            env.renew_channel(n_veh, size_platoon)
            env.renew_channels_fastfading()
        state_old = [get_state(env=env, idx=i) for i in range(n_platoon)]
        for i_step in range(n_step_per_episode):
            at = np.zeros([n_platoon, n_output], dtype=int)
            for i in range(n_platoon):
                a = np.clip(agents[i].choose_action(state_old[i]), -0.999, 0.999)
                at[i, 0] = ((a[0] + 1) / 2) * n_RB
                at[i, 1] = ((a[1] + 1) / 2) * n_S
                at[i, 2] = np.round(np.clip(((a[2] + 1) / 2) * max_power, 1, max_power))
            _, _, _, _, platoon_AoI, C_rate, V_rate, Demand_R, V2V_success = env.act_for_training(at.copy())
            env.renew_channels_fastfading()
            env.Compute_Interference(at.copy())
            for i in range(n_platoon):
                aoi_evo[i, t, i_step] = platoon_AoI[i]
                pow_evo[i, t, i_step] = at[i, 2]
            state_old = [get_state(env=env, idx=i) for i in range(n_platoon)]
    return aoi_evo, pow_evo


def write_seamless_outputs(run_dir, sfx, aoi_evo, pow_evo):
    viol = (aoi_evo.astype(np.float64) > env.tau_aoi).mean(axis=(1, 2))   # per-platoon over the whole tail
    viol_ep = (aoi_evo.astype(np.float64) > env.tau_aoi).mean(axis=2)     # per-platoon per-episode trajectory
    scipy.io.savemat(os.path.join(run_dir, 'AoI_evolution_seamless%s.mat' % sfx), {'AoI_evolution_seamless': aoi_evo})
    scipy.io.savemat(os.path.join(run_dir, 'power_seamless%s.mat' % sfx), {'power_seamless': pow_evo})
    scipy.io.savemat(os.path.join(run_dir, 'viol_rate_seamless%s.mat' % sfx), {'viol_rate_seamless': viol})
    scipy.io.savemat(os.path.join(run_dir, 'viol_rate_seamless_ep%s.mat' % sfx), {'viol_rate_seamless_ep': viol_ep})
    print('  [seamless%s] tail viol/platoon = %s  worst = %.3f  net-mean = %.3f'
          % (sfx, np.round(viol, 3), float(viol.max()), float(viol.mean())))
    return viol


def save_scenario_reconstruct(run_dir, ep_offset, lam_I_state=None, lam_err_prev_state=None):
    # Full end-of-training snapshot so a later run can branch from the EXACT ep_offset state
    # (sigma-sweep / online-dual) via --seamless_resume. RNG states captured HERE so a resume at
    # the same sigma reproduces this inline tail. The whole env object is pickled (vehicles /
    # positions / AoI / channels / shadowing), so nothing stateful is missed.
    recon = {
        'env': env,
        'rng_random': random.getstate(),
        'rng_numpy': np.random.get_state(),
        'rng_torch': T.get_rng_state(),
        'rng_torch_cuda': (T.cuda.get_rng_state_all() if T.cuda.is_available() else None),
        'lam_per_platoon': np.array([agents[j].lam for j in range(n_platoon)], dtype=np.float64),
        'lam_I': (None if lam_I_state is None else np.asarray(lam_I_state, dtype=np.float64)),
        'lam_err_prev': (None if lam_err_prev_state is None else np.asarray(lam_err_prev_state, dtype=np.float64)),
        'ep_offset': int(ep_offset),
        'seed': SEED, 'mode': CONSTRAINT_MODE, 'tau': float(env.tau_aoi), 'eps': float(env.eps_viol),
        'dual': args.dual, 'n_platoon': int(n_platoon),
    }
    path = os.path.join(run_dir, 'Scenario_Reconstruct.pkl')
    with open(path, 'wb') as f:
        pickle.dump(recon, f, protocol=pickle.HIGHEST_PROTOCOL)
    print('  [seamless] saved scenario reconstruct ->', path)
    return path
# ------------------------------------------------------------------------------------------------------------------ #
if IS_TRAIN:
    '''
    The following three lines can be used to load the saved models
    '''
    # global_agent.load_models()
    # for i in range(n_platoon):
    #     agents[i].load_models()
    # [RQ1-CMDP] PID-Lagrangian per-platoon state (only used when --dual pid).
    #   lam_I = integral accumulator (plays lambda's role in the pure-integral law);
    #   lam_err_prev = previous-episode error for the derivative term.
    lam_I = np.zeros(n_platoon, dtype=np.float64)
    lam_err_prev = np.zeros(n_platoon, dtype=np.float64)
    for i_episode in range(n_episode):
        done = False
        # [RQ1-CMDP] sigma-anneal: linearly lower the actor exploration noise over
        #   training. Default off -> agent.noise stays the constant 0.3 set at
        #   construction (i.e. this whole block is a no-op unless --sigma_anneal).
        if args.sigma_anneal:
            frac = (i_episode / (n_episode - 1)) if n_episode > 1 else 0.0
            cur_sigma = args.sigma_start + (args.sigma_end - args.sigma_start) * frac
            for ag in agents:
                ag.noise = cur_sigma
        print("-------------------------------------------------------------------------------------------------------")
        record_reward_t1 = np.zeros([n_platoon, n_step_per_episode], dtype=np.float16)
        record_reward_t2 = np.zeros([n_platoon, n_step_per_episode], dtype=np.float16)
        record_reward_cost = np.zeros([n_platoon, n_step_per_episode], dtype=np.float16)   # [RQ1-CMDP]
        record_reward_global = np.zeros([n_step_per_episode], dtype=np.float16)
        record_AoI = np.zeros([n_platoon, n_step_per_episode], dtype=np.float16)
        record_Jain = np.zeros([n_step_per_episode], dtype=np.float16)
        for ag in agents:   # [RQ1-CMDP] reset the per-episode cost-critic diagnostics
            ag.diag_closs_sum = 0.0
            ag.diag_force_sum = 0.0
            ag.diag_n = 0

        env.V2V_demand = env.V2V_demand_size * np.ones(n_platoon, dtype=np.float16)
        env.individual_time_limit = env.time_slow * np.ones(n_platoon, dtype=np.float16)
        env.active_links = np.ones((int(env.n_Veh / env.size_platoon)), dtype='bool')
        if i_episode == 0:
            env.AoI = np.ones(int(n_platoon)) * 100

        if i_episode % 20 == 0:
            env.renew_positions()                   # update vehicle position
            env.renew_channel(n_veh, size_platoon)  # update channel slow fading
            env.renew_channels_fastfading()         # update channel fast fading

        state_old_all = []
        for i in range(n_platoon):
            state = get_state(env=env, idx=i)
            state_old_all.append(state)

        for i_step in range(n_step_per_episode):
            state_new_all = []
            action_all = []
            action_all_training = np.zeros([n_platoon, n_output], dtype=int)  # [RQ1-CMDP] np.int removed in numpy>=1.24
            # receive observation
            for i in range(n_platoon):
                action = agents[i].choose_action(state_old_all[i])
                action = np.clip(action, -0.999, 0.999)
                action_all.append(action)

                action_all_training[i, 0] = ((action[0]+1)/2) * n_RB  # chosen RB
                action_all_training[i, 1] = ((action[1]+1)/2) * n_S  # Inter/Intra platoon mode
                action_all_training[i, 2] = np.round(np.clip(((action[2]+1)/2) * max_power, 1, max_power))  # power selected by PL

            # All the agents take actions simultaneously, obtain reward, and update the environment
            action_temp = action_all_training.copy()
            task_1_r, task_2_r, global_reward, cost_aoi, platoon_AoI, C_rate, V_rate, Demand_R, V2V_success = \
                env.act_for_training(action_temp)
            for i in range(n_platoon):
                record_reward_t1[i, i_step] = task_1_r[i]
                record_reward_t2[i, i_step] = task_2_r[i]
                record_reward_cost[i, i_step] = cost_aoi[i]   # [RQ1-CMDP] cost-critic reward signal
                record_AoI[i, i_step] = env.AoI[i]
            record_reward_global[i_step] = global_reward
            record_Jain[i_step] = env.compute_jain_aoi()

            if writer is not None:
                global_step = i_episode * n_step_per_episode + i_step
                writer.add_scalar('step/global_reward', float(global_reward), global_step)
                writer.add_scalar('step/mean_task1_reward', float(np.mean(task_1_r)), global_step)
                writer.add_scalar('step/mean_task2_reward', float(np.mean(task_2_r)), global_step)
                writer.add_scalar('step/mean_aoi', float(np.mean(platoon_AoI)), global_step)
                writer.add_scalar('step/jain_index', float(record_Jain[i_step]), global_step)
                writer.add_scalar('step/mean_v2i_rate', float(np.mean(C_rate)), global_step)
                writer.add_scalar('step/mean_v2v_rate', float(np.mean(V_rate)), global_step)
                writer.add_scalar('step/mean_remaining_demand', float(np.mean(Demand_R)), global_step)
                writer.add_scalar('step/v2v_success', float(V2V_success), global_step)
                writer.add_scalar('step/mean_power', float(np.mean(action_temp[:, 2])), global_step)

            env.renew_channels_fastfading()
            env.Compute_Interference(action_temp)
            # get new state
            for i in range(n_platoon):
                state_new = get_state(env, i)
                state_new_all.append(state_new)

            if i_step == n_step_per_episode - 1:
                done = True

            # taking the agents actions, states and reward (+ per-platoon cost)
            memory.store_transition(np.asarray(state_old_all).flatten(), np.asarray(action_all).flatten(),
                                    global_reward, task_1_r, task_2_r, cost_aoi,
                                    np.asarray(state_new_all).flatten(), done)

            # agents take random samples and learn
            if memory.mem_cntr >= batch_size:
                states, actions, rewards_g, rewards_t1, rewards_t2, rewards_cost, states_, dones = \
                    memory.sample_buffer(batch_size)

                global_agent.global_learn(agents, states, actions, rewards_g, rewards_t1, rewards_t2,
                                          rewards_cost, states_, dones)

            # old observation = new_observation
            for i in range(n_platoon):
                state_old_all[i] = state_new_all[i]
            print('Episode:', i_episode)
            #print('iteration:', i_step)
            #print('agents task 1 rewards :\n', task_1_r)
            #print('agents task 2 rewards :\n', task_2_r)
            #print('agents global rewards :\n', global_reward)

            for i in range(n_platoon):
                AoI_evolution[i, i_episode % 100, i_step] = platoon_AoI[i]
                Demand_total[i, i_episode % 100, i_step] = Demand_R[i]
                V2I_total[i, i_episode % 100, i_step] = C_rate[i]
                V2V_total[i, i_episode % 100, i_step] = V_rate[i]
                power_total[i, i_episode % 100, i_step] = action_temp[i, 2]

        record_reward_t1_[:, i_episode] = np.mean(record_reward_t1, axis=1)
        record_reward_t2_[:, i_episode] = np.mean(record_reward_t2, axis=1)
        record_reward_cost_[:, i_episode] = np.mean(record_reward_cost, axis=1)        # [RQ1-CMDP] cost reward
        record_reward_total_[:, i_episode] = record_reward_t1_[:, i_episode] + record_reward_t2_[:, i_episode]  # [RQ1-CMDP] total task reward (t1+t2)
        record_reward_global_[i_episode] = np.mean(record_reward_global)
        AoI_total[:, i_episode] = np.mean(record_AoI, axis=1)
        Jain_total[i_episode] = np.mean(record_Jain)

        # [RQ1-CMDP] per-platoon episodic violation rate  P(AoI_j > tau).
        viol_rate = np.mean(record_AoI > env.tau_aoi, axis=1)     # (n_platoon,)
        viol_total[:, i_episode] = viol_rate
        # [RQ1-CMDP] per-episode cost-critic diagnostics (0 until the buffer fills and
        # learning starts; pure logging).
        for j in range(n_platoon):
            dn = max(agents[j].diag_n, 1)
            critic_loss_cost_total[j, i_episode] = agents[j].diag_closs_sum / dn
            cost_force_total[j, i_episode] = agents[j].diag_force_sum / dn
        # Two-timescale dual ascent (slow loop): raise lambda_j when platoon j
        # exceeds its target violation probability, lower it otherwise.
        if CONSTRAINT_MODE == 'hard':
            # [RQ1-CMDP #3] error signal that drives the dual ascent.
            #   per_platoon : each platoon j uses its OWN violation error (ours).
            #   global_mean : ONE shared error = network-mean violation - eps.
            #   global_max  : ONE shared error = worst-platoon violation - eps.
            # global_* broadcast the SAME error to every j, so all lambda_j stay
            # identical -> effectively a single global multiplier. The default
            # 'per_platoon' branch is numerically IDENTICAL to the original law.
            if args.lam_scope == 'per_platoon':
                e_vec = viol_rate - env.eps_viol
            elif args.lam_scope == 'global_mean':
                e_vec = np.full(n_platoon, float(np.mean(viol_rate)) - env.eps_viol)
            else:  # global_max
                e_vec = np.full(n_platoon, float(np.max(viol_rate)) - env.eps_viol)
            if args.dual == 'integral':
                # original pure-integral law (per_platoon path is byte-for-byte).
                for j in range(n_platoon):
                    new_lam = agents[j].lam + args.eta_lam * e_vec[j]
                    agents[j].lam = float(np.clip(new_lam, 0.0, args.lam_max))
            else:
                # [RQ1-CMDP] PID-Lagrangian (Stooke 2020) on e=(error_j).
                #   I_j   <- clip(I_j + ki*e, 0, lam_max)            (integral)
                #   lam_j  = clip(kp*e + I_j + kd*(e - e_prev), 0, lam_max)
                # With kp=kd=0, ki=eta_lam this reduces to the integral law above.
                for j in range(n_platoon):
                    e = e_vec[j]
                    lam_I[j] = float(np.clip(lam_I[j] + args.ki * e, 0.0, args.lam_max))
                    deriv = e - lam_err_prev[j]
                    lam_pid = args.kp * e + lam_I[j] + args.kd * deriv
                    agents[j].lam = float(np.clip(lam_pid, 0.0, args.lam_max))
                    lam_err_prev[j] = e
        lambda_total[:, i_episode] = np.array([agents[j].lam for j in range(n_platoon)])
        print('  [%s] ep %d  viol_rate=%s  lambda=%s'
              % (CONSTRAINT_MODE, i_episode, np.round(viol_rate, 3),
                 np.round(lambda_total[:, i_episode], 2)))

        if writer is not None:
            episode_slot = i_episode % n_episode_test
            writer.add_scalar('episode/global_reward', float(record_reward_global_[i_episode]), i_episode)
            writer.add_scalar('episode/mean_task1_reward', float(np.mean(record_reward_t1_[:, i_episode])), i_episode)
            writer.add_scalar('episode/mean_task2_reward', float(np.mean(record_reward_t2_[:, i_episode])), i_episode)
            writer.add_scalar('episode/mean_aoi', float(np.mean(AoI_total[:, i_episode])), i_episode)
            writer.add_scalar('episode/jain_index', float(Jain_total[i_episode]), i_episode)
            writer.add_scalar('episode/mean_v2i_rate', float(np.mean(V2I_total[:, episode_slot, :])), i_episode)
            writer.add_scalar('episode/mean_v2v_rate', float(np.mean(V2V_total[:, episode_slot, :])), i_episode)
            writer.add_scalar('episode/mean_remaining_demand', float(np.mean(Demand_total[:, episode_slot, :])), i_episode)
            writer.add_scalar('episode/mean_power', float(np.mean(power_total[:, episode_slot, :])), i_episode)
            for i in range(n_platoon):
                writer.add_scalar('episode/task1_reward_per_agent/agent_%d' % i,
                                  float(record_reward_t1_[i, i_episode]), i_episode)
                writer.add_scalar('episode/task2_reward_per_agent/agent_%d' % i,
                                  float(record_reward_t2_[i, i_episode]), i_episode)
                writer.add_scalar('episode/aoi_per_agent/agent_%d' % i,
                                  float(AoI_total[i, i_episode]), i_episode)

        if i_episode % 50 == 0:
            global_agent.save_models()
            for i in range(n_platoon):
                agents[i].save_models()

    print('Training Done. Saving models...')
    current_dir = os.path.dirname(os.path.realpath(__file__))
    os.makedirs(os.path.join(current_dir, "model", label), exist_ok=True)  # [RQ1-CMDP]

    reward_path_t1 = os.path.join(current_dir, "model/" + label + '/reward_t1.mat')
    reward_path_t2 = os.path.join(current_dir, "model/" + label + '/reward_t2.mat')
    reward_path_cost = os.path.join(current_dir, "model/" + label + '/reward_cost.mat')      # [RQ1-CMDP]
    reward_path_total = os.path.join(current_dir, "model/" + label + '/reward_total.mat')    # [RQ1-CMDP]
    closs_path = os.path.join(current_dir, "model/" + label + '/critic_loss_cost.mat')       # [RQ1-CMDP]
    cforce_path = os.path.join(current_dir, "model/" + label + '/cost_force.mat')            # [RQ1-CMDP]
    AoI_path = os.path.join(current_dir, "model/" + label + '/AoI.mat')
    Jain_path = os.path.join(current_dir, "model/" + label + '/Jain.mat')
    viol_path = os.path.join(current_dir, "model/" + label + '/viol_rate.mat')
    lambda_path = os.path.join(current_dir, "model/" + label + '/lambda.mat')
    AoI_evolution_path = os.path.join(current_dir, "model/" + label + '/AoI_evolution.mat')
    Demand_path = os.path.join(current_dir, "model/" + label + '/demand.mat')
    V2I_path = os.path.join(current_dir, "model/" + label + '/V2I.mat')
    V2V_path = os.path.join(current_dir, "model/" + label + '/V2V.mat')
    power_path = os.path.join(current_dir, "model/" + label + '/power.mat')

    scipy.io.savemat(reward_path_t1, {'reward_t1': record_reward_t1_})
    scipy.io.savemat(reward_path_t2, {'reward_t2': record_reward_t2_})
    scipy.io.savemat(reward_path_cost, {'reward_cost': record_reward_cost_})       # [RQ1-CMDP]
    scipy.io.savemat(reward_path_total, {'reward_total': record_reward_total_})     # [RQ1-CMDP]
    # [RQ1-CMDP] reward_global.mat is intentionally no longer written (inert at the actor
    # due to the retained detached global-critic; older runs still contain it).
    scipy.io.savemat(closs_path, {'critic_loss_cost': critic_loss_cost_total})      # [RQ1-CMDP]
    scipy.io.savemat(cforce_path, {'cost_force': cost_force_total})                 # [RQ1-CMDP]
    scipy.io.savemat(AoI_path, {'AoI': AoI_total})
    scipy.io.savemat(Jain_path, {'Jain': Jain_total})
    scipy.io.savemat(viol_path, {'viol_rate': viol_total})         # [RQ1-CMDP]
    scipy.io.savemat(lambda_path, {'lambda': lambda_total})        # [RQ1-CMDP]
    scipy.io.savemat(AoI_evolution_path, {'AoI_evolution': AoI_evolution})
    scipy.io.savemat(Demand_path, {'demand': Demand_total})
    scipy.io.savemat(V2I_path, {'V2I': V2I_total})
    scipy.io.savemat(V2V_path, {'V2V': V2V_total})
    scipy.io.savemat(power_path, {'power': power_total})

    global_agent.save_models()
    for i in range(n_platoon):
        agents[i].save_models()

    # [RQ1-CMDP] frozen-deployment evaluation (default off; --eval_episodes 0).
    if args.eval_episodes > 0:
        run_deploy_eval_suite()

    # [RQ1-CMDP] SEAMLESS frozen-deployment tail (default off; --seamless_tail 0). Runs strictly
    #   AFTER the training loop + .mat/model save, so the first n_episode episodes are byte-for-byte
    #   the normal training run (verify by diffing viol_rate/lambda/AoI_evolution vs Canonical_ep600).
    #   Saves the ep-offset reconstruct, then continues the SAME env frozen for --seamless_tail eps.
    if args.seamless_tail > 0:
        run_dir = os.path.join(current_dir, "model", label)
        os.makedirs(run_dir, exist_ok=True)
        save_scenario_reconstruct(run_dir, n_episode, lam_I_state=lam_I, lam_err_prev_state=lam_err_prev)
        aoi_tail, pow_tail = run_seamless_tail(args.seamless_tail, n_episode, args.seamless_noise)
        write_seamless_outputs(run_dir, '', aoi_tail, pow_tail)

# [RQ1-CMDP] eval-only: load the frozen policies from this run's checkpoints and run ONLY
# the deployment eval (no training, no buffer, no dual). RQ1_CKPT_SUBDIR must point at the
# SAME per-run checkpoint subdir the training run used (REMOTE_RUNBOOK §3). Note: eval A
# here starts from the seed's initial geometry (no training preceded) — still in-distribution.
if args.eval_only:
    print('=== [RQ1-CMDP] eval-only: loading agent checkpoints (RQ1_CKPT_SUBDIR=%s) ==='
          % os.environ.get('RQ1_CKPT_SUBDIR', 'tmp/ddpg'))
    for i in range(n_platoon):
        agents[i].load_models()
    if args.eval_episodes > 0:
        run_deploy_eval_suite()

# [RQ1-CMDP] SEAMLESS RESUME: branch from a saved Scenario_Reconstruct.pkl (sigma-sweep /
#   online-dual from the EXACT ep_offset state). Restores env + RNG + dual in place, loads this
#   run's frozen checkpoints, runs a frozen tail at --seamless_noise. Writes *_seamless_n{NN}.mat
#   so multiple sigma never clobber. No training (IS_TRAIN forced 0 above).
if args.seamless_resume:
    if args.seamless_tail <= 0:
        raise SystemExit('[seamless-resume] also pass --seamless_tail N (>0) to run the tail')
    print('=== [RQ1-CMDP] seamless-resume from %s (sigma=%.2g, tail=%d) ==='
          % (args.seamless_resume, args.seamless_noise, args.seamless_tail))
    with open(args.seamless_resume, 'rb') as f:
        recon = pickle.load(f)
    env.__dict__.update(recon['env'].__dict__)          # restore full env state in place
    random.setstate(recon['rng_random'])
    np.random.set_state(recon['rng_numpy'])
    T.set_rng_state(recon['rng_torch'])
    if recon.get('rng_torch_cuda') is not None and T.cuda.is_available():
        T.cuda.set_rng_state_all(recon['rng_torch_cuda'])
    for i in range(n_platoon):
        agents[i].load_models()
    for j in range(n_platoon):
        agents[j].lam = float(recon['lam_per_platoon'][j])
    run_dir = os.path.join(current_dir, "model", label)
    os.makedirs(run_dir, exist_ok=True)
    sfx = '_n%d' % round(args.seamless_noise * 100)
    aoi_tail, pow_tail = run_seamless_tail(args.seamless_tail, int(recon['ep_offset']), args.seamless_noise)
    write_seamless_outputs(run_dir, sfx, aoi_tail, pow_tail)

if writer is not None:
    writer.close()

end = time.time()
print("simulation took this much time ... ", end - start)
