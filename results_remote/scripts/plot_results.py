import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import scipy.io


def load_mat_files(result_dir):
    data = {}
    for path in sorted(result_dir.glob("*.mat")):
        mat = scipy.io.loadmat(path)
        keys = [key for key in mat.keys() if not key.startswith("__")]
        if len(keys) == 1:
            data[keys[0]] = np.asarray(mat[keys[0]], dtype=np.float64)
        else:
            for key in keys:
                data[key] = np.asarray(mat[key], dtype=np.float64)
    return data


def save_current_figure(result_dir, filename):
    plt.tight_layout()
    plt.savefig(result_dir / filename, dpi=200, bbox_inches="tight")
    plt.close()


def empirical_cdf(values):
    values = np.sort(np.asarray(values, dtype=np.float64).ravel())
    if values.size == 0:
        return values, values
    probability = np.arange(1, values.size + 1, dtype=np.float64) / values.size
    return values, probability


def plot_task_rewards(result_dir, data):
    if "reward_t1" not in data or "reward_t2" not in data:
        return

    reward_t1 = data["reward_t1"]
    reward_t2 = data["reward_t2"]
    avg_t1 = np.mean(reward_t1, axis=0)
    avg_t2 = np.mean(reward_t2, axis=0)

    plt.figure("Task Decomposition Rewards", figsize=(8, 5))
    plt.plot(avg_t1, color="blue", linewidth=1.5, label="Task 1: V2V Demand")
    plt.plot(avg_t2, color="red", linewidth=1.5, label="Task 2: V2I & AoI")
    plt.grid(True)
    plt.xlabel("Episode")
    plt.ylabel("Local Reward")
    plt.title("Convergence of Decomposed Tasks")
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2)
    save_current_figure(result_dir, "Algo1_Result_1_Task_Rewards.png")


def plot_global_reward(result_dir, data):
    if "reward_global" not in data:
        return

    reward_global = data["reward_global"]
    if reward_global.ndim > 1 and reward_global.shape[0] > 1:
        avg_global = np.mean(reward_global, axis=0)
    else:
        avg_global = reward_global.squeeze()

    plt.figure("Global Reward", figsize=(8, 5))
    plt.plot(avg_global, color=(0.4660, 0.6740, 0.1880), linewidth=1.5)
    plt.grid(True)
    plt.title("Global System Performance (Interference Mitigation)")
    plt.xlabel("Episode")
    plt.ylabel("Global Reward")
    save_current_figure(result_dir, "Algo1_Result_2_Global_Reward.png")


def plot_jain_index(result_dir, data):
    if "Jain" not in data:
        return

    jain = data["Jain"]
    if jain.ndim > 1 and jain.shape[0] > 1:
        avg_jain = np.mean(jain, axis=0)
    else:
        avg_jain = jain.squeeze()

    plt.figure("Jain Fairness Index", figsize=(8, 5))
    plt.plot(avg_jain, color=(0.4940, 0.1840, 0.5560), linewidth=1.5)
    plt.grid(True)
    plt.title("Jain Fairness Index over AoI")
    plt.xlabel("Episode")
    plt.ylabel("Jain Index")
    plt.ylim(0, 1.05)
    save_current_figure(result_dir, "Algo1_Result_7_Jain_Index.png")


def plot_aoi_cdf(result_dir, data):
    if "AoI" not in data:
        return

    aoi = data["AoI"]
    stable_aoi = aoi[:, -100:] if aoi.ndim == 2 and aoi.shape[1] >= 100 else aoi
    aoi_vector = stable_aoi.ravel()
    x, f = empirical_cdf(aoi_vector)
    if x.size == 0:
        return

    p90 = np.percentile(aoi_vector, 90)
    plt.figure("AoI CDF", figsize=(8, 5))
    plt.plot(x, f, linewidth=2, color=(0, 0.4470, 0.7410))
    plt.axvline(p90, ymin=0, ymax=0.9 / 1.05, color="red", linestyle="--")
    plt.text(p90, 0.4, "  90th Percentile: %.2f" % p90, color="red")
    plt.grid(True)
    plt.xlabel("Age of Information (AoI)")
    plt.ylabel("Probability (P <= x)")
    plt.title("CDF of Average AoI (Last 100 Episodes)")
    plt.xlim(0, float(np.max(x)) * 1.1)
    plt.ylim(0, 1.05)
    save_current_figure(result_dir, "Algo1_Result_3_AoI_CDF.png")


def plot_aoi_evolution(result_dir, data):
    if "AoI_evolution" not in data:
        return

    aoi_evolution = data["AoI_evolution"]
    last_episode_aoi = np.squeeze(np.mean(aoi_evolution[:, -1, :], axis=0))

    plt.figure("AoI Real-time Evolution", figsize=(8, 5))
    plt.plot(last_episode_aoi, color=(0.3010, 0.7450, 0.9330), linewidth=2)
    plt.grid(True)
    plt.title("Intra-Episode: AoI Sawtooth Evolution (Algorithm 1)")
    plt.xlabel("Step")
    plt.ylabel("Instantaneous AoI")
    plt.ylim(0, float(np.max(last_episode_aoi)) + 5)
    save_current_figure(result_dir, "Algo1_Result_4_AoI_Evolution.png")


def plot_demand(result_dir, data):
    if "demand" not in data:
        return

    demand = data["demand"]
    last_demand = np.squeeze(np.mean(demand[:, -1, :], axis=0))

    plt.figure("V2V Demand Depletion", figsize=(8, 5))
    plt.plot(last_demand, color="magenta", linewidth=2)
    plt.grid(True)
    plt.title("Intra-Episode: V2V Demand Depletion")
    plt.xlabel("Step")
    plt.ylabel("Remaining Demand (bits)")
    save_current_figure(result_dir, "Algo1_Result_5_Demand_Step.png")


def plot_rate_comparison(result_dir, data):
    if "V2I" not in data or "V2V" not in data:
        return

    v2i = data["V2I"]
    v2v = data["V2V"]
    mean_v2i = np.squeeze(np.mean(np.mean(v2i, axis=0), axis=0))
    mean_v2v = np.squeeze(np.mean(np.mean(v2v, axis=0), axis=0))

    plt.figure("Rate Comparison", figsize=(8, 5))
    plt.plot(mean_v2i, color="red", linewidth=1.5, label="V2I Rate (Cellular)")
    plt.plot(mean_v2v, color="black", linewidth=1.5, label="V2V Rate (Vehicle)")
    plt.grid(True)
    plt.legend()
    plt.title("Algorithm 1: Multi-Task Transmission Rate")
    plt.xlabel("Step")
    plt.ylabel("Rate (bps)")
    save_current_figure(result_dir, "Algo1_Result_6_Rate_Comparison.png")


def plot_aoi_trend(result_dir, data):
    if "AoI" not in data:
        return

    aoi = data["AoI"]
    avg_aoi = np.mean(aoi, axis=0)

    plt.figure("AoI Trend", figsize=(8, 5))
    plt.plot(avg_aoi, color=(0, 0.4470, 0.7410), linewidth=1.5)
    plt.grid(True)
    plt.title("Algorithm 1: Average AoI per Episode")
    plt.xlabel("Episode")
    plt.ylabel("Average AoI")
    save_current_figure(result_dir, "Algo1_Result_3_AoI_Trend.png")


def main():
    parser = argparse.ArgumentParser(
        description="Generate result figures from .mat files in a training result directory."
    )
    parser.add_argument(
        "result_dir",
        nargs="?",
        default=".",
        help="Directory containing .mat files. Defaults to the current directory.",
    )
    args = parser.parse_args()

    result_dir = Path(args.result_dir).resolve()
    if not result_dir.is_dir():
        raise SystemExit("Result directory does not exist: %s" % result_dir)

    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.grid": True,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "font.size": 11,
        "lines.linewidth": 1.5,
    })

    data = load_mat_files(result_dir)
    if not data:
        raise SystemExit("No .mat files found in: %s" % result_dir)

    plot_task_rewards(result_dir, data)
    plot_global_reward(result_dir, data)
    plot_jain_index(result_dir, data)
    plot_aoi_cdf(result_dir, data)
    plot_aoi_evolution(result_dir, data)
    plot_demand(result_dir, data)
    plot_rate_comparison(result_dir, data)
    plot_aoi_trend(result_dir, data)

    print("Generated figures in: %s" % result_dir)


if __name__ == "__main__":
    main()
