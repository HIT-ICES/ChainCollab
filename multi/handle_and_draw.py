import json
import matplotlib.pyplot as plt

# 读取 JSON 数据
with open('./result.json', "r") as f:
    content = json.load(f)

result = {}

# 处理数据
for item in content:
    if item["test_target"] not in result:
        result[item["test_target"]] = {
            "data_list": [],
        }
    result[item["test_target"]]["data_list"].append(item)

for key in result:
    data_list = result[key]["data_list"]
    
    sum_time = 0
    for item in data_list:
        sum_time += float(item["gocost"])
    result[key]["avg_gocost"] = sum_time / len(data_list)

    sum_time = 0
    for item in data_list:
        sum_time += float(item["trancost"])
    result[key]["avg_trancost"] = sum_time / len(data_list)

# 准备绘图
test_targets = sorted(result.keys(), key=lambda x: float(x))
avg_gocosts = [result[key]["avg_gocost"] for key in test_targets]
avg_trancosts = [result[key]["avg_trancost"] for key in test_targets]

# 创建图形
fig, ax1 = plt.subplots()

# 绘制 avg_gocost 曲线
ax1.set_xlabel('number of the  parallel Participant Layer machines')
ax1.set_ylabel('Average Statecharts Execution Cost (ms)', color='b')  # 这里添加了单位ms
ax1.plot(test_targets, avg_gocosts, marker='o', color='b', label='avg_statechartCost')
ax1.tick_params(axis='y', labelcolor='b')

# 设置左轴最大值为400
ax1.set_ylim(0, 400)

# 创建第二个 y 轴
ax2 = ax1.twinx()  
ax2.set_ylabel('Average Total Cost (ms)', color='r')  # 这里添加了单位ms
ax2.plot(test_targets, avg_trancosts, marker='o', color='r', label='avg_TotalCost')
ax2.tick_params(axis='y', labelcolor='r')

# 设置右侧坐标轴从0开始，并设置最大值为3000
ax2.set_ylim(0, 3000)  

# 添加虚线在 y=2000 处
ax2.axhline(y=2000, color='gray', linestyle='--', label='block generation interval')
ax2.annotate('block generation interval=2000ms', xy=(0, 2000), xytext=(2.5, 1700), 
             textcoords='data', ha='center', color='gray', fontsize=10,
             arrowprops=dict(facecolor='gray', arrowstyle='->'))

# 绘制垂直的虚线并标注“Maximum”
ax1.axvline(x=test_targets[-1], color='purple', linestyle='-', label='Firefly limitation(default)')
ax1.annotate('Firefly limitation=1M', xy=(test_targets[-1], 50),  
             xytext=(8, 30),  # Adjust Y value as necessary for text position
             textcoords='data', ha='center', color='purple',
             arrowprops=dict(facecolor='purple', arrowstyle='->'))

ax1.grid(True)

# 添加图例并调整位置以避免遮挡
fig.legend(loc="lower left", bbox_to_anchor=(0.15, 0.3))

# 保存图像
plt.savefig('myplot.png')