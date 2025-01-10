import json
from typing import List

import json
from translator.parser import Choreography
from translator.elements import (
    Element,
    StartEvent,
    ParallelGateway,
    ExclusiveGateway,
    EventBasedGateway,
    NodeType,
    EdgeType,
    EndEvent,
)

ident = 0

def print():
    pass



def method_to_extract_parallel_gateway(choreography: Choreography):
    def is_split_parallel_gateway(element):
        return element.type == NodeType.PARALLEL_GATEWAY and len(element.outgoings) > 1

    def is_merged_parallel_gateway(element):
        return element.type == NodeType.PARALLEL_GATEWAY and len(element.incomings) > 1

    def print_machine(machine):
        # 1. print the element of machine in order
        # 2. match if a nested machine is start with current element
        # 3. print the nested machine start with current element recursively

        for element in machine["direct_elements"]:
            print(element)
            if element in machine["nested_machines"]:
                print_machine(machine["nested_machines"][element])

        # Parallel Gateway

    def next_elements(source_element) -> list[Element]:
        if source_element.type == NodeType.END_EVENT:
            return []
        if source_element.type in (NodeType.PARALLEL_GATEWAY, NodeType.EXCLUSIVE_GATEWAY, NodeType.EVENT_BASED_GATEWAY):
            return [edge.target for edge in source_element.outgoings]
        if source_element.type in NodeType:
            return [source_element.outgoing.target]
        return []

    def handle_parallel_gateway(start_element, outer_machine) -> Element:
        # 0. scan all path
        # 1. Create a new machine for every path
        # 2. Add all the elements between the start_element and end_element to the new machine
        # 3. If there is a gateway in the middle, call this function recursively
        # 4. Add the new machine to the outer machine
        # 5. Return the end_element of the new machine
        def find_merged_parallel_gateway(start_element) -> Element:
            # find the merged one for start_element parallel gateway
            # Attention  There may be Cycle
            count = 1
            current_element = start_element
            while count != 0:
                current_element = next_elements(current_element)[0]  # always choose the first one to find the end
                if is_split_parallel_gateway(current_element):
                    count += 1
                if is_merged_parallel_gateway(current_element):
                    count -= 1
            end_element = current_element
            return end_element

        end_element = find_merged_parallel_gateway(start_element)
        
        print(f"START: handle elements between {start_element.id} and {end_element.id}")


        for idx, element in enumerate(next_elements(start_element)):
            # generate a new machine for every path
            new_machine = blank_machine.copy()
            new_machine["start_element"] = start_element
            new_machine["machine_name"] = f"{start_element.id} to {end_element.id} path {idx}"

            cursor = element
            print("FOR", element.id)
            print(end_element.id)
            while cursor.id != end_element.id:
                print(cursor.id)
                if not is_split_parallel_gateway(cursor):
                    new_machine["direct_elements"].append(cursor)
                    cursor = next_elements(cursor)[0]  # Emit Situation But Parallel Gateway
                    continue
                if is_split_parallel_gateway(cursor):
                    new_machine["direct_elements"].append(cursor)
                    end_element = handle_parallel_gateway(cursor, new_machine)
                    new_machine["direct_elements"].append(end_element)
                    cursor = end_element
                    continue

            outer_machine["nested_machines"][element] = new_machine
        
        print(f"END:handle elements between {start_element.id} and {end_element.id} ")

        return end_element

    def handle_exclusive_gateway(start_element, outer_machine) -> Element:
        # 1. Create a new machine
        # 2. Add all the elements between the start_element and end_element to the new machine
        # 3. If there is a gateway in the middle, call this function recursively
        # 4. Add the new machine to the outer machine
        # 5. Return the end_element of the new machine
        pass

    start_element = choreography.query_element_with_type(NodeType.START_EVENT)[0]
    end_element = choreography.query_element_with_type(NodeType.END_EVENT)[0]

    machine = {
        "start_element": start_element,  # commonly is startElement or a Gateway
        "machine_name": f"{start_element.id} to {end_element.id}",
        "direct_elements": [],
        "nested_machines": {},
    }

    blank_machine = {"start_element": None, "machine_name": "", "direct_elements": [], "nested_machines": {}}

    cursor = start_element
    while cursor.id != end_element.id:
        if cursor.type not in [NodeType.PARALLEL_GATEWAY]:
            machine["direct_elements"].append(cursor)
            assert len(next_elements(cursor)) == 1
            cursor = next_elements(cursor)[0]
            continue
        if cursor.type == NodeType.PARALLEL_GATEWAY:
            machine["direct_elements"].append(cursor)
            end_element = handle_parallel_gateway(cursor, machine)
            machine["direct_elements"].append(end_element)
            cursor = next_elements(end_element)[0]


if "__main__" == __name__:
    choreography = Choreography()
    choreography.load_diagram_from_xml_file("./bpmn_muti/parallel.bpmn")
    res = method_to_extract_parallel_gateway(choreography)


# TODO:1.Ondone连接               1.1.事件网关 得特殊处理，和ondone冲突。后面应该还是要统一处理ondone和这个网关。 1.2.排他条件网关=ondone+condition
# TODO:2.并行网关-->并行状态机 
# TODO:3.MutiParticipantMachine   3.1 第一次  3.2 后续
# TODO:4.MutiTaskMachine          4.1 MutiTaskPallelMachine





# 主状态机
mainMachine = {
    "context": {},
    "id": "",
    "initial": "",
    "states": {},
}


# actions：DMN结果，激活mutiparticipant,MutiTask循环自增 等函数
# guards：mutiparticipant条件，网关条件，mutiTask跳出条件
additionalContent = {
    "actions": {},
    "services": {},
    "guards": {},
    "delays": {},
}


def initMachine(id, initmachine):
    mainMachine["id"] = id
    mainMachine["initial"] = initmachine



def SetOndone(baseMachine,targetName):
    baseMachine["onDone"] = {"target": targetName, "actions": []}



#处理条件排他网关
#targetList: 
"""
onDone: [
          {
            target: "confirmation2",
            cond: "finalPriorityLow",
            actions: [],
          },
          {
            target: "confirmation3",
            cond: "finalPriorityMedium",
            actions: [],
          },
          {
            target: "confirmation4",
            cond: "finalPriorityHigh",
            actions: [],
          },
          {
            target: "confirmation1",
            cond: "finalPriorityVeryLow",
            actions: [],
          },
        ],
"""
def SetConditionOndone(baseMachine,targetList):
    

    """
    finalPriorityLow: (context, event) => {
        return context.finalPriority === "Low";
      },
    """
    for target in targetList:
        baseMachine["onDone"].update({"target": target["targetName"], "cond": target["conditionName"], "actions": []})
    #TODO:
 

def singleMessageMachine(baseMachine, messageName, *targetName):
    newData = {
        messageName: {
            "initial": "enable",
            "states": {
                "enable": {"on": {"next1-1": [{"target": "wait for confirm", "actions": []}]}},
                "wait for confirm": {"on": {"next1-2": [{"target": "done", "actions": []}]}},
                "done": {"type": "final"},
            },
        }
    }

    if targetName:
        newData[messageName]["onDone"] = {"target": targetName, "actions": []}

    baseMachine["states"].update(newData)


def parallelGatewayMachine(level):

    # TODO：在parser里解析出层级关系，并基于这个层级关系，递归拼装这个并行网关状态机，
    # Gateway_0onpe6x---Gateway_1fbifca
    #    transport order forwarding
    #        mem2_participant1
    #        mem3_participant1
    #        mem1_participant1
    #    supply order forwarding

    # 最后类似于这样。lock不用管，后面会写一个函数统一增强逻辑

    """
    "Gateway_0onpe6x---Gateway_1fbifca": {
        states: {
          "transport order forwarding": {
            initial: "transport order forwarding--unlocked",
            states: {
              "transport order forwarding--unlocked": {
                states: {
                  mem2_participant1: {
                    initial: "enable",
                    states: {
                      enable: {
                        on: {
                          "next2-2-1": [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      "wait for confirm": {
                        on: {
                          "next2-2-2": [
                            {
                              target: "done",
                              actions: [],
                            },
                          ],
                        },
                      },
                      done: {
                        entry: {
                          type: "activate_mem2_participant1",
                        },
                      },
                    },
                  },
                  mem3_participant1: {
                    initial: "enable",
                    states: {
                      enable: {
                        on: {
                          "next2-3-1": [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      "wait for confirm": {
                        on: {
                          "next2-3-2": [
                            {
                              target: "done",
                              actions: [],
                            },
                          ],
                        },
                      },
                      done: {
                        entry: {
                          type: "activate_mem3_participant1",
                        },
                      },
                    },
                  },
                  mem1_participant1: {
                    initial: "enable",
                    states: {
                      enable: {
                        on: {
                          "next2-1-1": [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      "wait for confirm": {
                        on: {
                          "next2-1-2": [
                            {
                              target: "done",
                              actions: [],
                            },
                          ],
                        },
                      },
                      done: {
                        entry: {
                          type: "activate_mem1_participant1",
                        },
                      },
                    },
                  },
                },
                on: {
                  advance: [
                    {
                      target: "transport order forwarding--locked",
                      actions: [],
                    },
                  ],
                },
                type: "parallel",
              },
              "transport order forwarding--locked": {
                type: "final",
              },
            },
          },
          "supply order forwarding": {
            initial: "enable",
            states: {
              enable: {
                on: {
                  "next1-1-1": [
                    {
                      target: "wait for confirm",
                      actions: [],
                    },
                  ],
                },
              },
              "wait for confirm": {
                on: {
                  "next1-1-2": [
                    {
                      target: "done",
                      actions: [],
                    },
                  ],
                },
              },
              done: {
                type: "final",
              },
            },
          },
        },
        type: "parallel",
        onDone: {
          target: "report details",
          actions: [],
        },
      },"""
    pass


def MutiTaskLoopMachine(
    basicMachine, name, targetName, loopMax, LoopConditionExpression, isMutiParticipant, *participants
):

    newData = {
        name: {
            "initial": "",
            "states": {},
            "onDone": [
                {
                    "target": name,
                    "cond": name + "_NotLoopMax",
                    "actions": [
                        {
                            "type": name + "_LoopAdd",
                        },
                    ],
                },
                {
                    "target": targetName,
                    "cond": name + "_LoopMax",
                    "actions": [],
                },
            ],
        }
    }

    if LoopConditionExpression:
        newData[name]["onDone"].append(
            {
                "target": targetName,
                "cond": name + "_LoopConditionMeet",
                "actions": [],
            }
        )

    if isMutiParticipant:
        newData[name]["type"] = "parallel"

        # TODO:如果同时是mutiparticiant的情况，则需要动态的拼接
        newData[name]["states"].update({})

        newData[name]["initial"] = participants[0]
    else:
        singleMessageMachine(newData[name], name)
        newData[name]["initial"] = "enable"

    LoopAdd = {
        name + "_LoopAdd": "assign({{{name}_loop: (context) => context.{name}_loop + 1}})".format(name=name),
    }
    ConditionLoopNotMax = {
        name
        + "_NotLoopMax": "(context, event) => {{return context.{name}_loop !== context.{name}_loopMax;}}".format(
            name=name
        ),
    }
    ConditionLoopMax = {
        name
        + "_LoopMax": "(context, event) => {{return context.{name}_loop === context.{name}_loopMax;}}".format(
            name=name
        ),
    }

    # TODO:这边==问题，先不管了。
    LoopConditionMeet = {
        name
        + "_LoopConditionMeet": "(context, event) => {{return context.{expression};}}".format(
            expression=LoopConditionExpression
        ),
    }

    basicMachine["states"].update(newData)
    basicMachine["context"].update({name + "_loop": 1, name + "_loopMax": loopMax})

    additionalContent["actions"].update(LoopAdd)
    additionalContent["guards"].update(ConditionLoopNotMax)
    additionalContent["guards"].update(ConditionLoopMax)
    if LoopConditionExpression:
        additionalContent["guards"].update(LoopConditionMeet)


def MutiTaskPallelMachine():
    pass


def DMNMachine(basicMachine, name, DMNOutput: List[str]):
    newData = {
        "priority decison": {
            "initial": "enable",
            "states": {
                "enable": {
                    "on": {
                        "next": [
                            {
                                "target": "done",
                                "actions": [name + "_setDMNResult" + "_{key}".format(key=key) for key in DMNOutput],
                            },
                        ],
                    },
                },
                "done": {
                    "type": "final",
                },
            },
            "onDone": [],
        },
    }

    basicMachine["states"].update(newData)

    # TODO:context可以扩展为更多类型
    # 把DMNOutput数组写入到context中
    basicMachine["context"].update({name + "_" + key: None for key in DMNOutput})

    # 如果有多个DMNresult
    additionalContent["actions"].update(
        {
            name
            + "_setDMNResult_{key}".format(
                key=key
            ): "assign({{{name}_{key}: (context,event) => event.values.{key}}})".format(name=name, key=key)
            for key in DMNOutput
        }
    )


def SetMachineFirstTime():
    pass
















initMachine("supplypaper", "Name1111")

singleMessageMachine(mainMachine, "Name1111", "Name2222")
singleMessageMachine(mainMachine, "Name2222", "Name3333")

MutiTaskLoopMachine(
    mainMachine, "cccc", "bbbbb", 5, "result==1", True, "mem1_participant1", "mem2_participant1", "mem3_participant1"
)

MutiTaskLoopMachine(mainMachine, "ddddd", "bbbbb", 5, None, False)

DMNMachine(mainMachine, "eeeee", ["result1", "result2", "result3"])


print(json.dumps(mainMachine, indent=4, ensure_ascii=False))
# 这一部分，函数需要去除引号
print(json.dumps(additionalContent, indent=4, ensure_ascii=False).replace('"', ""))
