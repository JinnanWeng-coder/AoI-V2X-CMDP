import random
import time
import os


class AoIModel:
    def __init__(self, n_platoons, dt_ms=1.0, max_aoi_ms=100.0, init_aoi_ms=None):
        self.n_platoons = n_platoons
        self.dt_ms = dt_ms
        self.max_aoi_ms = max_aoi_ms
        init_val = max_aoi_ms if init_aoi_ms is None else init_aoi_ms
        self.aoi = [float(init_val)] * n_platoons

    def reset(self, value_ms=None):
        val = self.max_aoi_ms if value_ms is None else value_ms
        self.aoi = [float(val)] * self.n_platoons

    def step(self, success_flags):
        next_aoi = []
        for i in range(self.n_platoons):
            if success_flags[i]:
                next_aoi.append(self.dt_ms)
            else:
                next_aoi.append(min(self.aoi[i] + self.dt_ms, self.max_aoi_ms))
        self.aoi = next_aoi
        return self.aoi


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def bar(value, max_value=100, width=40):
    filled = int((value / max_value) * width)
    return "█" * filled + "·" * (width - filled)


def build_realtime_text(slot, aoi_values, success_flags, probs):
    lines = []
    lines.append(f"AoI terminal demo | slot = {slot}\n")
    lines.append("说明: SUCCESS -> 本时隙成功更新到RSU, AoI重置为1; FAIL -> AoI加1\n")

    for i, (aoi, succ, p) in enumerate(zip(aoi_values, success_flags, probs)):
        status = "SUCCESS" if succ else "FAIL   "
        lines.append(
            f"Platoon {i+1:>2} | p={p:.2f} | {status} | "
            f"AoI={aoi:>5.1f} ms | {bar(aoi)}"
        )
    return "\n".join(lines)


def ascii_history_plot(history, max_aoi=100, height=12):
    n_platoons = len(history)
    n_steps = len(history[0])

    symbols = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    canvas = [[" " for _ in range(n_steps)] for _ in range(height)]

    for idx in range(n_platoons):
        series = history[idx]
        sym = symbols[idx % len(symbols)]
        for t, val in enumerate(series):
            row = height - 1 - int((val / max_aoi) * (height - 1))
            row = max(0, min(height - 1, row))
            canvas[row][t] = sym

    lines = []
    lines.append("\nAoI 历史曲线（终端版）")
    lines.append("纵轴: AoI, 横轴: slot")
    for r in range(height):
        y = max_aoi * (height - 1 - r) / (height - 1)
        lines.append(f"{y:>6.1f} | " + "".join(canvas[r]))
    lines.append("       +" + "-" * (n_steps + 2))
    lines.append("         " + "".join(str(i % 10) for i in range(n_steps)))
    lines.append("\n图例:")
    for i in range(n_platoons):
        lines.append(f"  {i+1} -> Platoon {i+1}")

    return "\n".join(lines)


def main():
    random.seed(42)

    n_platoons = 3
    n_slots = 60
    dt_ms = 1.0
    max_aoi = 100.0
    success_probs = [0.85, 0.15, 0.45]

    model = AoIModel(
        n_platoons=n_platoons,
        dt_ms=dt_ms,
        max_aoi_ms=max_aoi,
        init_aoi_ms=20.0
    )

    history = [[] for _ in range(n_platoons)]
    log_path = "aoi_log.txt"

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("AoI 仿真日志\n")
        f.write("=" * 80 + "\n\n")

        for slot in range(n_slots):
            success_flags = [random.random() < p for p in success_probs]
            aoi_values = model.step(success_flags)

            for i in range(n_platoons):
                history[i].append(aoi_values[i])

            frame_text = build_realtime_text(slot, aoi_values, success_flags, success_probs)

            # 终端显示
            clear_screen()
            print(frame_text)

            # 写入 txt
            f.write(frame_text + "\n")
            f.write("-" * 80 + "\n")
            f.flush()

            time.sleep(0.15)

        summary_lines = []
        summary_lines.append("\n仿真结束。\n")
        for i in range(n_platoons):
            avg_aoi = sum(history[i]) / len(history[i])
            summary_lines.append(f"Platoon {i+1}: 平均 AoI = {avg_aoi:.2f} ms")

        plot_text = ascii_history_plot(history, max_aoi=max_aoi, height=12)

        clear_screen()
        print("\n".join(summary_lines))
        print(plot_text)

        f.write("\n".join(summary_lines) + "\n")
        f.write(plot_text + "\n")

    print(f"\n日志已保存到: {log_path}")


if __name__ == "__main__":
    main()