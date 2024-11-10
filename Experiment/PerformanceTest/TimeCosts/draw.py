import matplotlib.pyplot as plt

# 定义每个步骤的名称和对应的耗时（单位：秒）
steps = ["Invoke", "Invoke Firefly", "Invoke Fabric", "Consensus Reached"]
time_durations = [5, 8, 10, 6]  # 假设的每个步骤的耗时

# 计算每个步骤的开始和结束时间
start_times = [0] + [sum(time_durations[:i]) for i in range(1, len(time_durations))]
end_times = [start + duration for start, duration in zip(start_times, time_durations)]

# 绘制时间线段图
fig, ax = plt.subplots(figsize=(10, 2))
for i, (start, end) in enumerate(zip(start_times, end_times)):
    ax.plot([start, end], [1, 1], color="skyblue", lw=6, solid_capstyle="butt")
    ax.text((start + end) / 2, 1.05, steps[i], ha="center", va="bottom", fontsize=12)

# 配置图形
ax.set_ylim(0.8, 1.2)
ax.set_xlim(0, sum(time_durations))
ax.set_yticks([])
ax.set_xticks(start_times + [sum(time_durations)])
ax.set_xticklabels(start_times + [sum(time_durations)], fontsize=10)
ax.set_title("步骤耗时时间线")

plt.show()
