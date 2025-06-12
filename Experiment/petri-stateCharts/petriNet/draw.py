import re
import matplotlib.pyplot as plt
from collections import defaultdict

N_invoke_times = defaultdict(list)

with open("./result.txt", "r") as f:
    current_N = None
    for line in f:
        m_N = re.search(r"Testing N=(\d+), K=(\d+)", line)
        if m_N:
            current_N = int(m_N.group(1))
        m_invoke = re.search(r"Invoke \d+ duration: (\d+)ms", line)
        if m_invoke and current_N is not None:
            invoke_time = int(m_invoke.group(1))
            N_invoke_times[current_N].append(invoke_time)

N_list = sorted(N_invoke_times.keys())
mean_invoke_list = [
    sum(times) / len(times) if times else 0
    for times in (N_invoke_times[N] for N in N_list)
]

plt.plot(N_list, mean_invoke_list, marker='o')
plt.xlabel("N (Number of Participants)")
plt.ylabel("Mean Invoke Duration (ms)")
plt.title("N vs Mean Invoke Duration")
plt.grid(True)

# 在每个点旁边标注散点值
for x, y in zip(N_list, mean_invoke_list):
    plt.text(x, y, f"{y:.1f}", ha='left', va='bottom', fontsize=8)

plt.savefig("mean_invoke_time.png")
plt.show()