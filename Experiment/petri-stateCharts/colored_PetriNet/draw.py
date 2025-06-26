import re
import matplotlib.pyplot as plt
from collections import defaultdict
import os
import numpy as np

# 设置路径和前缀匹配条件
base_path = "./"
file_prefix = "result-06.26-k3"  # 可根据需要修改前缀匹配模式

N_invoke_times = defaultdict(list)

# 遍历匹配的文件
for fname in os.listdir(base_path):
    if fname.startswith(file_prefix) and fname.endswith(".txt"):
        with open(os.path.join(base_path, fname), "r") as f:
            current_N = None
            for line in f:
                m_N = re.search(r"Testing N=(\d+), K=(\d+)", line)
                if m_N:
                    current_N = int(m_N.group(1))
                m_invoke = re.search(r"Invoke \d+ duration: (\d+)ms", line)
                if m_invoke and current_N is not None:
                    invoke_time = int(m_invoke.group(1))
                    N_invoke_times[current_N].append(invoke_time)

# 异常值过滤
filtered_N_invoke_times = {}
for N, times in N_invoke_times.items():
    times_np = np.array(times)
    mean = times_np.mean()
    std = times_np.std()
    lower = mean - 1.5 * std
    upper = mean + 1.5 * std
    filtered = times_np[(times_np >= lower) & (times_np <= upper)]
    filtered_N_invoke_times[N] = filtered.tolist()
    print(f"N={N}, Original={len(times)}, Filtered={len(filtered)}")

# 绘图
N_list = sorted(filtered_N_invoke_times.keys())
mean_invoke_list = [
    sum(times) / len(times) if times else 0
    for times in (filtered_N_invoke_times[N] for N in N_list)
]

plt.plot(N_list, mean_invoke_list, marker="o")
plt.xlabel("N (Number of Participants)")
plt.ylabel("Mean Invoke Duration (ms)")
plt.title("N vs Mean Invoke Duration (Filtered)")
plt.grid(True)

# 添加标注
for x, y in zip(N_list, mean_invoke_list):
    plt.text(x, y, f"{y:.1f}", ha="left", va="bottom", fontsize=8)

plt.tight_layout()
plt.savefig("mean_invoke_time_foltered_k3_06.26.png")
plt.show()
