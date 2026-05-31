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
parser.add_argument('--episodes', type=int, default=500)
parser.add_argument('--seed', type=int, default=2)
parser.add_argument('--tau', type=float, default=8.0, help='AoI threshold (slots)')
parser.add_argument('--eps', type=float, default=0.10, help='target violation prob.')
parser.add_argument('--eta_lam', type=float, default=3.0, help='dual step size')
parser.add_argument('--lam_max', type=float, default=20.0, help='multiplier clip')
parser.add_argument('--smoke', action='store_true', help='tiny end-to-end test run')
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
IS_TRAIN = 1
IS_TEST = 1 - IS_TRAIN
label = 'marl_model_' + CONSTRAINT_MODE + '_seed' + str(SEED)   # [RQ1-CMDP] separate soft/hard/seed outputs

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
n_veh = 20  # n_platoon * size_platoon
n_platoon = int(n_veh / size_platoon)  # number of platoons
n_RB = 3  # number of resource blocks
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
env.aoi_penalty_coef = 0.0 if CONSTRAINT_MODE == 'hard' else (1.0 / 20)

n_episode = args.episodes
n_step_per_episode = int(env.time_slow / env.time_fast)
n_episode_test = 100  # test episodes
if args.smoke:                       # tiny end-to-end sanity run
    n_episode = 3
    n_step_per_episode = 20
    n_episode_test = 3
print('=== RQ1 run: mode=%s seed=%d episodes=%d tau=%.1f eps=%.2f smoke=%s ==='
      % (CONSTRAINT_MODE, SEED, n_episode, args.tau, args.eps, args.smoke))
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
record_reward_global_ = np.zeros([n_episode], dtype=np.float16)
Jain_total = np.zeros([n_episode], dtype=np.float16)
# [RQ1-CMDP] per-platoon, per-episode violation rate and multiplier traces.
# These two are the headline RQ1 outputs (soft vs hard comparison).
viol_total = np.zeros([n_platoon, n_episode], dtype=np.float32)
lambda_total = np.zeros([n_platoon, n_episode], dtype=np.float32)
# ------------------------------------------------------------------------------------------------------------------ #
if IS_TRAIN:
    '''
    The following three lines can be used to load the saved models
    '''
    # global_agent.load_models()
    # for i in range(n_platoon):
    #     agents[i].load_models()
    for i_episode in range(n_episode):
        done = False
        print("-------------------------------------------------------------------------------------------------------")
        record_reward_t1 = np.zeros([n_platoon, n_step_per_episode], dtype=np.float16)
        record_reward_t2 = np.zeros([n_platoon, n_step_per_episode], dtype=np.float16)
        record_reward_global = np.zeros([n_step_per_episode], dtype=np.float16)
        record_AoI = np.zeros([n_platoon, n_step_per_episode], dtype=np.float16)
        record_Jain = np.zeros([n_step_per_episode], dtype=np.float16)

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
            action_all_training = np.zeros([n_platoon, n_output], dtype=np.int)
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
        record_reward_global_[i_episode] = np.mean(record_reward_global)
        AoI_total[:, i_episode] = np.mean(record_AoI, axis=1)
        Jain_total[i_episode] = np.mean(record_Jain)

        # [RQ1-CMDP] per-platoon episodic violation rate  P(AoI_j > tau).
        viol_rate = np.mean(record_AoI > env.tau_aoi, axis=1)     # (n_platoon,)
        viol_total[:, i_episode] = viol_rate
        # Two-timescale dual ascent (slow loop): raise lambda_j when platoon j
        # exceeds its target violation probability, lower it otherwise.
        if CONSTRAINT_MODE == 'hard':
            for j in range(n_platoon):
                new_lam = agents[j].lam + args.eta_lam * (viol_rate[j] - env.eps_viol)
                agents[j].lam = float(np.clip(new_lam, 0.0, args.lam_max))
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
    reward_path_global = os.path.join(current_dir, "model/" + label + '/reward_global.mat')
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
    scipy.io.savemat(reward_path_global, {'reward_global': record_reward_global_})
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

if writer is not None:
    writer.close()

end = time.time()
print("simulation took this much time ... ", end - start)
