from matplotlib import font_manager
import matplotlib.pyplot as plt
import math
import matplotlib.colors as mcolors
import json

# 尝试指定一种字体，如果系统中存在 "SimHei"（黑体），可以直接使用
plt.rcParams["font.sans-serif"] = ["SimHei"]  # 如果没有可以尝试 "Arial" 或其他字体
plt.rcParams["axes.unicode_minus"] = False  # 避免负号显示异常


with open("BRT.json", "r", encoding="utf-8") as f:
    data = json.load(f)


steps = [data_item["step"] for data_item in data]
start_times = [data_item["start_time"] for data_item in data]
end_times = [data_item["end_time"] for data_item in data]


min_time = min(start_times)
start_times = [start - min_time for start in start_times]
end_times = [end - min_time for end in end_times]


durations = [end - start for start, end in zip(start_times, end_times)]
scaled_start_times = [math.log10(start + 1) for start in start_times]
scaled_durations = [math.log10(duration + 1) for duration in durations]


num_steps = len(steps)
colors = list(mcolors.TABLEAU_COLORS.values())[:num_steps]

fig, ax = plt.subplots(figsize=(12, 6))
tick_positions = []
tick_labels = []
for i, (step, start, duration, origin_start, origin_end) in enumerate(zip(steps, start_times, durations, start_times, end_times)):
    ax.barh(
        step, duration, left=start, color=colors[i % len(colors)], edgecolor="black", linewidth=1, alpha=0.8, height=0.4
    )
    tick_positions.append(start)
    tick_labels.append(f"{origin_start}ms")
    tick_positions.append(start + duration)
    tick_labels.append(f"{origin_end}ms")

# for i, (start, duration) in enumerate(zip(scaled_start_times, scaled_durations)):
#     ax.text(
#         start + duration / 2,
#         i,
#         f"{round(10**duration - 1)}ms",
#         va="center",
#         ha="center",
#         color="white",
#         fontsize=11,
#         fontweight="bold",
#     )

ax.set_xlabel("时间轴（ 毫秒）", fontsize=12, fontweight="bold")
# 不均衡，手动指定位置处显示时间

# 排序 position, label
tick_positions, tick_labels = zip(*sorted(zip(tick_positions, tick_labels)))
tick_positions = list(tick_positions)
tick_labels = list(tick_labels)

# 检查position, 如果下一个离上一个过近, <0.1, 则去掉 position 与 label
remove_index = []
for i in range(1, len(tick_positions)):
    if tick_positions[i] - tick_positions[i - 1] < 0.1:
        remove_index.append(i)
for i in remove_index[::-1]:
    tick_positions.pop(i)
    tick_labels.pop(i)


ax.set_xticks(tick_positions, tick_labels, rotation=45)

ax.set_ylabel("步骤", fontsize=12, fontweight="bold")
ax.set_title("步骤耗时时间线（对数缩放）", fontsize=16, fontweight="bold", color="#4e79a7")
ax.invert_yaxis()
ax.grid(True, linestyle="--", alpha=0.6)




plt.subplots_adjust(left=0.15, right=0.95, top=0.85, bottom=0.1)
plt.show()
