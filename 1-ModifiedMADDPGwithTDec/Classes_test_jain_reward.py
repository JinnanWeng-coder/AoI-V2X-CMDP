import os
import sys

import numpy as np


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CLASSES_DIR = os.path.join(CURRENT_DIR, "Classes")
sys.path.insert(0, CLASSES_DIR)

from Environment_Platoon import Environ


def make_env():
    up_lanes = [i / 2.0 for i in
                [3.5 / 2, 3.5 / 2 + 3.5, 250 + 3.5 / 2, 250 + 3.5 + 3.5 / 2,
                 500 + 3.5 / 2, 500 + 3.5 + 3.5 / 2]]
    down_lanes = [i / 2.0 for i in
                  [250 - 3.5 - 3.5 / 2, 250 - 3.5 / 2, 500 - 3.5 - 3.5 / 2,
                   500 - 3.5 / 2, 750 - 3.5 - 3.5 / 2, 750 - 3.5 / 2]]
    left_lanes = [i / 2.0 for i in
                  [3.5 / 2, 3.5 / 2 + 3.5, 433 + 3.5 / 2, 433 + 3.5 + 3.5 / 2,
                   866 + 3.5 / 2, 866 + 3.5 + 3.5 / 2]]
    right_lanes = [i / 2.0 for i in
                   [433 - 3.5 - 3.5 / 2, 433 - 3.5 / 2, 866 - 3.5 - 3.5 / 2,
                    866 - 3.5 / 2, 1299 - 3.5 - 3.5 / 2, 1299 - 3.5 / 2]]

    width = 750 / 2
    height = 1298 / 2
    size_platoon = 4
    n_veh = 20
    n_RB = 3
    Gap = 25
    V2I_min = 540
    bandwidth = int(180000)
    V2V_size = int((4000) * 8)

    return Environ(down_lanes, up_lanes, left_lanes, right_lanes, width, height,
                   n_veh, size_platoon, n_RB, V2I_min, bandwidth, V2V_size, Gap)


env = make_env()
env.new_random_game()
n_pl = int(env.n_Veh / env.size_platoon)

env.AoI = np.array([10.0] * n_pl)
j = env.compute_jain_aoi()
print(f"Equal AoI: Jain = {j:.4f}  (expected 1.0000)")
assert abs(j - 1.0) < 1e-6, "Jain should be 1.0 for equal AoI"

env.AoI = np.array([100.0] + [0.0] * (n_pl - 1))
j = env.compute_jain_aoi()
print(f"One-hot AoI: Jain = {j:.4f}  (expected {1.0 / n_pl:.4f})")
assert abs(j - 1.0 / n_pl) < 1e-3, "Jain should be ~1/n for one-hot AoI"

env.AoI = np.array([5, 8, 6, 7, 4][:n_pl])
j = env.compute_jain_aoi()
print(f"Mixed AoI: Jain = {j:.4f}  (expected ~0.97)")
assert 0.9 < j < 1.0

env.Interference_all = np.full(n_pl, -100.0)
env.AoI = np.array([6.0] * n_pl)
interf_term = -np.mean((env.Interference_all + 60) / 60)
jain_term = env.compute_jain_aoi()
combined = interf_term + env.LAMBDA_JAIN * jain_term
print(f"Interference term = {interf_term:.4f} (should be ~0.67)")
print(f"Jain term         = {jain_term:.4f} (should be 1.0)")
print(f"LAMBDA_JAIN       = {env.LAMBDA_JAIN}")
print(f"Combined reward   = {combined:.4f} (should be ~0.97 = 0.67 + 0.3*1.0)")

env = make_env()
env.new_random_game()
n_pl = int(env.n_Veh / env.size_platoon)
env.V2V_demand = env.V2V_demand_size * np.ones(n_pl, dtype=np.float16)
env.individual_time_limit = env.time_slow * np.ones(n_pl, dtype=np.float16)
env.active_links = np.ones(n_pl, dtype='bool')
env.AoI = np.ones(n_pl) * 100

env.renew_positions()
env.renew_channel(env.n_Veh, env.size_platoon)
env.renew_channels_fastfading()

print("\n=== 10 random-action steps ===")
for step in range(10):
    actions = np.zeros((n_pl, 3), dtype=np.int_)
    actions[:, 0] = np.random.randint(0, env.n_RB, size=n_pl)
    actions[:, 1] = np.random.randint(0, 2, size=n_pl)
    actions[:, 2] = np.random.randint(1, 31, size=n_pl)
    out = env.act_for_training(actions)
    t1, t2, gr, aoi, _, _, _, _ = out
    j_check = env.compute_jain_aoi()
    print(f"step {step}: gr={gr:.4f}  AoI mean={np.mean(aoi):.2f}  Jain={j_check:.3f}")
    env.renew_channels_fastfading()
    env.Compute_Interference(actions)

print("\nAll tests passed if no assertion errors and rewards look reasonable.")
