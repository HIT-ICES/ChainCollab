import re
import matplotlib.pyplot as plt
from collections import defaultdict
import os
import numpy as np

def parse_multiple_result_files(dir_path, file_prefix):
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
                        # if invoke_time < 2000:
                        #     print(
                        #         f"Warning: Invoke time {invoke_time}ms is less than 2000ms for N={current_N}. Adjusting to 2000ms."
                        #     )
                        #     invoke_time += 2000
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

# 修改路径和前缀
petri_dir = "/home/shenxz-lab/code/ChainCollab/Experiment/petri-stateCharts/colored_PetriNet/"
statecharts_dir = "/home/shenxz-lab/code/ChainCollab/Experiment/petri-stateCharts/stateCharts/"
dag_dir = "/home/shenxz-lab/code/ChainCollab/Experiment/petri-stateCharts/DAG/"
file_prefix = "result-06.23-k3"  # 例如 "result-06.23-k3"

# 分别处理 Colored Petri Net 和 StateCharts 的数据
N_list_petri, mean_invoke_petri = parse_multiple_result_files(petri_dir, file_prefix)
N_list_state, mean_invoke_state = parse_multiple_result_files(statecharts_dir, file_prefix)
N_list_dag, mean_invoke_dag = parse_multiple_result_files(dag_dir, file_prefix)

# 绘图
plt.plot(N_list_petri, mean_invoke_petri, marker="o", label="Color-PetriNet")
plt.plot(N_list_state, mean_invoke_state, marker="s", label="StateCharts")
plt.plot(N_list_dag, mean_invoke_dag, marker="^", label="DAG")

plt.xlabel("N (Number of Participants)")
plt.ylabel("Mean Invoke Duration (ms)")
plt.title("N vs Mean Invoke Duration For Color-PetriNet, StateCharts, and DAG")
plt.grid(True)
plt.legend()

# 标注散点值
# 将三条线的数据统一到一个结构中
from collections import defaultdict

points_by_x = defaultdict(list)
for x, y in zip(N_list_petri, mean_invoke_petri):
    points_by_x[x].append(("PetriNet", y))
for x, y in zip(N_list_state, mean_invoke_state):
    points_by_x[x].append(("StateCharts", y))
for x, y in zip(N_list_dag, mean_invoke_dag):
    points_by_x[x].append(("DAG", y))

# 标注散点值，防止重叠
for x in sorted(points_by_x.keys()):
    y_values = sorted(points_by_x[x], key=lambda t: t[1], reverse=True)  # 按 y 值降序排列
    for idx, (label, y) in enumerate(y_values):
        if idx == 0:
            va, dy = "bottom", 3   # 最高的往上偏移
        elif idx == 1:
            va, dy = "center", 0   # 中间的居中
        else:
            va, dy = "top", -3     # 最低的往下偏移

        # 水平偏移可自定义，也可以不加
        if label == "PetriNet":
            ha = "left"
        elif label == "StateCharts":
            ha = "right"
        else:
            ha = "center"

        plt.text(x, y + dy, f"{y:.1f}", ha=ha, va=va, fontsize=8)


plt.tight_layout()
plt.savefig("compare_color_statecharts_dag_filtered.png")
plt.show()
