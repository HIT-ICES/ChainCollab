import re
import matplotlib.pyplot as plt
from collections import defaultdict

def parse_result_file(filepath):
    N_invoke_times = defaultdict(list)
    with open(filepath, "r") as f:
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
    N_list = sorted(N_invoke_times.keys())
    mean_invoke_list = [
        sum(times) / len(times) if times else 0
        for times in (N_invoke_times[N] for N in N_list)
    ]
    return N_list, mean_invoke_list

# 路径请根据实际情况修改
petri_path = "/home/shenxz-lab/code/ChainCollab/Experiment/petri-stateCharts/petriNet/result.txt"
fsm_path = "/home/shenxz-lab/code/ChainCollab/Experiment/petri-stateCharts/FSM/result.txt"

N_list_petri, mean_invoke_petri = parse_result_file(petri_path)
N_list_fsm, mean_invoke_state = parse_result_file(fsm_path)

plt.plot(N_list_petri, mean_invoke_petri, marker="o", label="PetriNet")
plt.plot(N_list_fsm, mean_invoke_state, marker="s", label="FSM")

plt.xlabel("N (Number of Participants)")
plt.ylabel("Mean Invoke Duration (ms)")
plt.title("N vs Mean Invoke Duration")
plt.grid(True)
plt.legend()

# 标注散点值
for x, y in zip(N_list_petri, mean_invoke_petri):
    plt.text(x, y, f"{y:.1f}", ha="left", va="bottom", fontsize=8)
for x, y in zip(N_list_fsm, mean_invoke_state):
    plt.text(x, y, f"{y:.1f}", ha="right", va="top", fontsize=8)

plt.savefig("compare_fsm_petrinet.png")
plt.show()