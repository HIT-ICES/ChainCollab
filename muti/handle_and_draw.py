import json
import matplotlib.pyplot as plt


with open('./result.json', "r") as f:
    content = json.load(f)


result = {}

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


test_targets = sorted(result.keys(), key=lambda x: float(x))
avg_gocosts = [result[key]["avg_gocost"] for key in test_targets]
avg_trancosts = [result[key]["avg_trancost"] for key in test_targets]


fig, ax = plt.subplots()
ax.plot(test_targets, avg_gocosts, marker='o', color='b', label='avg_gocost')


for i, txt in enumerate(avg_gocosts):
    ax.annotate(f"{txt:.2f}", (test_targets[i], avg_gocosts[i]), textcoords="offset points", xytext=(0,10), ha='center')


ax.set_title("Average GoCost vs Test Target")
ax.set_xlabel('Test Target')
ax.set_ylabel('Average GoCost')
ax.legend()
ax.grid(True)


plt.show()


fig, ax = plt.subplots()
ax.plot(test_targets, avg_trancosts, marker='o', color='r', label='avg_trancost')


for i, txt in enumerate(avg_trancosts):
    ax.annotate(f"{txt:.2f}", (test_targets[i], avg_trancosts[i]), textcoords="offset points", xytext=(0,10), ha='center')

ax.set_title("Average TranCost vs Test Target")
ax.set_xlabel('Test Target')
ax.set_ylabel('Average TranCost')
ax.legend()
ax.grid(True)


plt.show()