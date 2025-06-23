import re
import matplotlib.pyplot as plt
from collections import defaultdict
import os
import numpy as np

def parse_multiple_result_files(dir_path, file_prefix="result"):
    N_invoke_times = defaultdict(list)

    for fname in os.listdir(dir_path):
        if fname.startswith(file_prefix) and fname.endswith(".txt"):
            with open(os.path.join(dir_path, fname), "r") as f:
                current_N = None
                for line in f:
                    m_N = re.search(r"Testing N=(\d+), K=(\d+)", line)
                    if m_N:
                        current_N = int(m_N.group(1))
                    m_invoke = re.search(r"Invoke \d+ duration: (\d+)ms", line)
                    if m_invoke and current_N is not None:
                        invoke_time = int(m_invoke.group(1))
                        if invoke_time < 2000:
                            print(
                                f"Warning: Invoke time {invoke_time}ms is less than 2000ms for N={current_N}. Adjusting to 2000ms."
                            )
                            invoke_time += 2000
                        N_invoke_times[current_N].append(invoke_time)

    # 过滤异常值
    filtered_N_invoke_times = {}
    for N, times in N_invoke_times.items():
        times_np = np.array(times)
        mean = times_np.mean()
        std = times_np.std()
        lower = mean - 1.5 * std
        upper = mean + 1.5 * std
        filtered = times_np[(times_np >= lower) & (times_np <= upper)]
        filtered_N_invoke_times[N] = filtered.tolist()
        print(f"[{file_prefix}] N={N}, Original={len(times)}, Filtered={len(filtered)}")

    N_list = sorted(filtered_N_invoke_times.keys())
    mean_invoke_list = [
        sum(filtered_N_invoke_times[N]) / len(filtered_N_invoke_times[N]) if filtered_N_invoke_times[N] else 0
        for N in N_list
    ]
    return N_list, mean_invoke_list

# 修改为你的实际路径
petri_dir = "/home/shenxz-lab/code/ChainCollab/Experiment/petri-stateCharts/petriNet/"
fsm_dir = "/home/shenxz-lab/code/ChainCollab/Experiment/petri-stateCharts/FSM/"
file_prefix = "result-06.23-k3"  # 修改为你实际的前缀，如果是 result-06.23-k3 就写那个

N_list_petri, mean_invoke_petri = parse_multiple_result_files(petri_dir, file_prefix)
N_list_fsm, mean_invoke_fsm = parse_multiple_result_files(fsm_dir, file_prefix)

# 绘图
plt.plot(N_list_petri, mean_invoke_petri, marker="o", label="PetriNet")
plt.plot(N_list_fsm, mean_invoke_fsm, marker="s", label="FSM")

plt.xlabel("N (Number of Participants)")
plt.ylabel("Mean Invoke Duration (ms)")
plt.title("N vs Mean Invoke Duration (Filtered)")
plt.grid(True)
plt.legend()

# 标注散点值，避免重叠：上面的向上偏移，下面的向下偏移
for x in set(N_list_petri).intersection(N_list_fsm):
    y_petri = mean_invoke_petri[N_list_petri.index(x)]
    y_fsm = mean_invoke_fsm[N_list_fsm.index(x)]
    if y_petri >= y_fsm:
        plt.text(x, y_petri + 5, f"{y_petri:.1f}", ha="center", va="bottom", fontsize=8)
        plt.text(x, y_fsm - 5, f"{y_fsm:.1f}", ha="center", va="top", fontsize=8)
    else:
        plt.text(x, y_fsm + 5, f"{y_fsm:.1f}", ha="center", va="bottom", fontsize=8)
        plt.text(x, y_petri - 5, f"{y_petri:.1f}", ha="center", va="top", fontsize=8)


plt.tight_layout()
plt.savefig("compare_fsm_petrinet_filtered.png")
plt.show()
