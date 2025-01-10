import json
from typing import List


# 1.Ondone连接               1.1.事件网关 得特殊处理，和ondone冲突。后面应该还是要统一处理ondone和这个网关。 1.2.排他条件网关=ondone+condition
# TODO:2.并行网关-->并行状态机
# 3.MutiParticipantMachine   3.1 第一次  3.2 后续
# TODO:4.MutiTaskMachine          4.1 MutiTaskPallelMachine

# 微调 1."next3-2-3"此类名称改为元素名称 -->手动改


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


def SetOndone(baseMachine, targetName):
    baseMachine["onDone"] = {"target": targetName, "actions": []}


# 处理条件排他网关
"""
targetList:[
          {
            targetName: "",
            condition: "",
          },
          {...},
        ],
"""
def ExclusiveGatewayMachine(baseMachine, targetList, name):
    newData = {
        name: {
            "always": [],
        },
    }

    for target in targetList:
        newData[name]["always"].append(
            {
                "target": target["targetName"],
                "cond": name + "__" + target["targetName"],
                "actions": [],
            }
        )
        additionalContent["guards"].update(
            {
                name
                + "__"
                + target[
                    "targetName"
                ]: "(context, event) => {{return context.{condition};}}".format(
                    condition=target["condition"]
                )
            }
        )
    baseMachine["states"].update(newData)


# 处理基于事件的网关
"""
targetList:[
          {
            targetName: "",
            event: "",
          },
          {...},
        ],
"""
def EventGatewayMachine(baseMachine, targetList, name):
    newData = {
        name: {
            "on": {},
        },
    }

    for target in targetList:
        newData[name]["on"].update(
            {
                target["event"]: [
                    {
                        "target": target["targetName"],
                        "actions": [],
                    },
                ]
            }
        )

    baseMachine["states"].update(newData)


def singleMessageMachine(baseMachine, name, targetName=None):
    newData = {
        name: {
            "initial": "enable",
            "states": {
                "enable": {
                    "on": {"next1-1": [{"target": "wait for confirm", "actions": []}]}
                },
                "wait for confirm": {
                    "on": {"next1-2": [{"target": "done", "actions": []}]}
                },
                "done": {"type": "final"},
            },
        }
    }

    if targetName:
        newData[name]["onDone"] = {"target": targetName, "actions": []}

    baseMachine["states"].update(newData)


def parallelGatewayMachine(level):

    # TODO：在parser里解析出层级关系，并基于这个层级关系，递归拼装这个并行网关状态机，
    # Gateway_0onpe6x---Gateway_1fbifca
    #    transport order forwarding
    #        mem2_participant1
    #        mem3_participant1
    #        mem1_participant1
    #    supply order forwarding

    # lock不用管，后面会写一个函数统一增强逻辑
    pass


def MutiTaskLoopMachine(
    basicMachine,
    name,
    loopMax,
    LoopConditionExpression,
    isMutiParticipant,
    targetName=None,
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
        pass
        # TODO:如果同时是mutiparticiant的情况，则需要动态的拼接

    else:
        singleMessageMachine(newData[name], name)
        newData[name]["initial"] = "enable"

    LoopAdd = {
        name
        + "_LoopAdd": "assign({{{name}_loop: (context) => context.{name}_loop + 1}})".format(
            name=name
        ),
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

    basicMachine["context"].update({name + "_loop": 1, name + "_loopMax": loopMax})

    additionalContent["actions"].update(LoopAdd)
    additionalContent["guards"].update(ConditionLoopNotMax)
    additionalContent["guards"].update(ConditionLoopMax)
    if LoopConditionExpression:
        additionalContent["guards"].update(LoopConditionMeet)

    if targetName:
        newData[name]["onDone"].append(
            {
                "target": targetName,
                "cond": name + "_LoopMax",
                "actions": [],
            }
        )
    basicMachine["states"].update(newData)


def MutiTaskPallelMachine():
    pass


def DMNMachine(basicMachine, name, DMNOutput: List[str], targetName=None):
    newData = {
        name: {
            "initial": "enable",
            "states": {
                "enable": {
                    "on": {
                        "next": [
                            {
                                "target": "done",
                                "actions": [
                                    name + "_setDMNResult" + "_{key}".format(key=key)
                                    for key in DMNOutput
                                ],
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

    if targetName:
        SetOndone(newData[name], targetName)

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
            ): "assign({{{name}_{key}: (context,event) => event.values.{key}}})".format(
                name=name, key=key
            )
            for key in DMNOutput
        }
    )


def MutiParticipantMachine(name, max, firstTime=False, targetName=None):

    newData = {
        name: {
            "initial": "machine1",
            "states": {},
            "onDone": [],
        },
    }

    machineDict = {}

    for index in range(1, max + 1):
        machineDict.update(
            {
                "machine"
                + str(index): {
                    "initial": "disable",
                    "states": {
                        "disable": {
                            "always": [
                                {
                                    "target": "enable",
                                    "cond": "active_" + name + "_machine_" + str(index),
                                    "actions": [],
                                },
                                {
                                    "target": "locked_done",
                                    "cond": "inactive_"
                                    + name
                                    + "_machine_"
                                    + str(index),
                                    "actions": [],
                                },
                            ],
                        },
                        "enable": {
                            "on": {
                                "next3-2-2": [
                                    {
                                        "target": "wait for confirm",
                                        "actions": [],
                                    },
                                ],
                            },
                        },
                        "locked_done": {
                            "type": "final",
                        },
                        "wait for confirm": {
                            "on": {
                                "next3-2-3": [
                                    {
                                        "target": "done",
                                        "actions": [],
                                    },
                                ],
                            },
                        },
                        "done": {
                            "type": "final",
                        },
                    },
                },
            }
        )

    if firstTime:
        newData[name]["states"].update(
            {
                "unlocked": {
                    "states": machineDict,
                    "on": {
                        "advance": [
                            {
                                "target": "transport order forwarding--locked",
                                "actions": [],
                            }
                        ]
                    },
                    "type": "parallel",
                }
            }
        )
        newData[name]["states"].update({"locked": {"type": "final"}})

    else:
        newData[name]["states"].update(machineDict)
        newData[name]["type"] = "parallel"

    if targetName:
        SetOndone(newData[name], targetName)

    mainMachine["states"].update(newData)





initMachine("supplypaper", "Name1111")

singleMessageMachine(mainMachine, "Name1111", "Name2222")
singleMessageMachine(mainMachine, "Name2222", "Name3333")

MutiTaskLoopMachine(mainMachine, "cccc", 5, "result==1", True, "bbbbb")
MutiTaskLoopMachine(mainMachine, "bbbbb", 5, None, False, "ddddd")

DMNMachine(mainMachine, "eeeee", ["result1", "result2", "result3"], "aaaa")

ExclusiveGatewayMachine(
    mainMachine,
    [
        {"targetName": "Name1111", "condition": "result==1"},
        {"targetName": "Name2222", "condition": "result==2"},
        {"targetName": "Name3333", "condition": "result==3"},
    ],
    "Gateway_111",
)
EventGatewayMachine(
    mainMachine,
    [
        {"targetName": "Name1111", "event": "event1"},
        {"targetName": "Name2222", "event": "event2"},
        {"targetName": "Name3333", "event": "event3"},
    ],
    "Gateway_222",
)


MutiParticipantMachine("jjjjjj", 3, False, "kkkkk")
MutiParticipantMachine("kkkkk", 3, True, "lllll")


print(json.dumps(mainMachine, indent=4, ensure_ascii=False))
# 这一部分，函数需要去除引号
print(
    json.dumps(additionalContent, indent=4, ensure_ascii=False)
    .replace('"', "")
    .replace("\\", "")
)