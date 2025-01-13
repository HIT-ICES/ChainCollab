import json
from typing import List


# 1.Ondone连接               1.1.事件网关 得特殊处理，和ondone冲突。后面应该还是要统一处理ondone和这个网关。 1.2.排他条件网关=ondone+condition
# TODO:2.并行网关-->并行状态机  在translator中实现？
# 3.MutiParticipantMachine   3.1 第一次  3.2 后续
# 4.MutiTaskMachine          4.1 MutiTaskPallelMachine

# 微调 1."next3-2-3"此类名称改为元素名称 -->手动改
# participant参数


class XstateJSONElement:

    def __init__(self):
        # 主状态机
        self.mainMachine = {
            "context": {},
            "id": "",
            "initial": "",
            "states": {},
        }

        # actions：DMN结果，激活mutiparticipant,MutiTask循环自增 等函数
        # guards：mutiparticipant条件，网关条件，mutiTask跳出条件
        self.additionalContent = {
            "actions": {},
            "services": {},
            "guards": {},
            "delays": {},
        }

    def initMainMachine(self,id, startEventName,targetName,endEventName):
        self.mainMachine["id"] = id
        self.mainMachine["initial"] = startEventName
        self.mainMachine["states"].update({
            startEventName: {
                "always": {
                "target": targetName,
                "actions": [],
                },
            }
        })
        self.mainMachine["states"].update({
            endEventName: {
                "type": "final",
            }
        })
        
        


    def SetOndone(self,baseMachine, targetName):
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
    def ExclusiveGatewayMachine(self,baseMachine, targetList, name):
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
            self.additionalContent["guards"].update(
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
    def EventGatewayMachine(self,baseMachine, targetList, name):
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


    def singleMessageMachine(self,baseMachine, name, targetName=None):
        newData = {
            name: {
                "initial": "enable",
                "states": {
                    "enable": {
                        "on": {"send_"+name: [{"target": "wait for confirm", "actions": []}]}
                    },
                    "wait for confirm": {
                        "on": {"confirm_"+name: [{"target": "done", "actions": []}]}
                    },
                    "done": {"type": "final"},
                },
            }
        }

        if targetName:
            newData[name]["onDone"] = {"target": targetName, "actions": []}

        baseMachine["states"].update(newData)


    def parallelGatewayMachine(self,level):

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
        self,
        baseMachine,
        name,
        loopMax,
        LoopConditionExpression,
        isMutiParticipant=False,
        targetName=None,
        MutiParticipantParam={}
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
                "type": "parallel",
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


        # ！这里可能有拼装问题。
        if isMutiParticipant:
            self.MutiParticipantMachine(newData[name], MutiParticipantParam["name"], MutiParticipantParam["max"], MutiParticipantParam["participantName"],MutiParticipantParam["firstTime"])
            newData[name]["initial"] = MutiParticipantParam["name"]

        else:
            self.singleMessageMachine(newData[name], name+"_instance")
            newData[name]["initial"] = name+"_instance"

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

        baseMachine["context"].update({name + "_loop": 1, name + "_loopMax": loopMax})

        self.additionalContent["actions"].update(LoopAdd)
        self.additionalContent["guards"].update(ConditionLoopNotMax)
        self.additionalContent["guards"].update(ConditionLoopMax)
        if LoopConditionExpression:
            self.additionalContent["guards"].update(LoopConditionMeet)

        if targetName:
            newData[name]["onDone"].append(
                {
                    "target": targetName,
                    "cond": name + "_LoopMax",
                    "actions": [],
                }
            )
        baseMachine["states"].update(newData)


    def MutiTaskPallelMachine(
        self,
        baseMachine,
        name,
        ParallelNum,
        isMutiParticipant=False,
        targetName=None,
        MutiParticipantParam={}):

        newData = {
            name: {
                "initial": "",
                "states": {},
                "type": "parallel",
                "onDone": [
                ],
            }
        }

        if isMutiParticipant:
            for index in range(1,ParallelNum+1):
                self.MutiParticipantMachine(newData[name], name+"_instance_"+str(index), MutiParticipantParam["max"],MutiParticipantParam["participantName"])
            newData[name]["initial"] = name+"_instance_1"

        else:
            for index in range(1,ParallelNum+1):
                self.singleMessageMachine(newData[name], name+"_instance_"+str(index))
            newData[name]["initial"] = name+"_instance_1"



        if targetName:
            newData[name]["onDone"] = {"target": targetName, "actions": []}

        baseMachine["states"].update(newData)




    def DMNMachine(self,baseMachine, name, DMNOutput: List[str], targetName=None):
        newData = {
            name: {
                "initial": "enable",
                "states": {
                    "enable": {
                        "on": {
                            "execute_DMN_"+name: [
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
            self.SetOndone(newData[name], targetName)

        baseMachine["states"].update(newData)

        # TODO:context可以扩展为更多类型
        # 把DMNOutput数组写入到context中
        baseMachine["context"].update({name + "_" + key: None for key in DMNOutput})

        # 如果有多个DMNresult
        self.additionalContent["actions"].update(
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


    def MutiParticipantMachine(self,baseMachine,name, max, participantName,firstTime=False, targetName=None):

        newData = {
            name: {
                "initial": "",
                "states": {},
                "onDone": [],
            },
        }

        machineDict = {}


        if firstTime:
            for index in range(1, max + 1):
                self.mainMachine["context"].update({participantName+"_machine_" + str(index): False})
                self.additionalContent["guards"].update(
                    {
                        "active_"+participantName+"_machine_" + str(index): "(context, event) => {return context."+participantName+"_machine_" + str(index)+";}",
                    }
                )
                self.additionalContent["guards"].update(
                    {
                        "inactive_"+participantName+"_machine_" + str(index): "(context, event) => {return !context."+participantName+"_machine_" + str(index)+";}",
                    }
                )
                self.additionalContent["actions"].update(
                    {
                        "activate_"+participantName+"_machine_" + str(index): "assign({"+participantName+"_machine_" + str(index)+":true})",
                    }
                )
                machineDict.update(
                    {
                        "machine_"
                        + str(index): {
                        "initial": "enable",
                        "states": {
                        "enable": {
                            "on": {
                            "send_"+name+"_machine"+str(index): [
                                {
                                "target": "wait for confirm",
                                "actions": [],
                                },
                            ],
                            },
                        },
                        "wait for confirm": {
                            "on": {
                            "confirm_"+name+"_machine"+str(index): [
                                {
                                "target": "done",
                                "actions": [],
                                },
                            ],
                            },
                        },
                        "done": {
                            "entry": {
                            "type": "activate_"+participantName+"_machine_" + str(index),
                            },
                        },
                        },
                    },
                    }
                )
            newData[name]["states"].update(
                {
                    "unlocked": {
                        "states": machineDict,
                        "on": {
                            "advance": [
                                {
                                    "target": "locked",
                                    "actions": [],
                                }
                            ]
                        },
                        "type": "parallel",
                    }
                }
            )
            newData[name]["states"].update({"locked": {"type": "final"}})
            newData[name]["initial"]="unlocked"

        else:
            for index in range(1, max + 1):
                machineDict.update(
                    {
                        "machine_"
                        + str(index): {
                            "initial": "disable",
                            "states": {
                                "disable": {
                                    "always": [
                                        {
                                            "target": "enable",
                                            "cond": "active_" + participantName + "_machine_" + str(index),
                                            "actions": [],
                                        },
                                        {
                                            "target": "locked_done",
                                            "cond": "inactive_"
                                            + participantName
                                            + "_machine_"
                                            + str(index),
                                            "actions": [],
                                        },
                                    ],
                                },
                                "enable": {
                                    "on": {
                                        "send_"+name+"_machine"+str(index): [
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
                                        "confirm_"+name+"_machine"+str(index): [
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
            newData[name]["states"].update(machineDict)
            newData[name]["type"] = "parallel"
            newData[name]["initial"]="machine_1"

        if targetName:
            self.SetOndone(newData[name], targetName)

        baseMachine["states"].update(newData)


    def ParallelGatewayMachine(
            self,
            baseMachine,
            name,
            Gatewaystruct,
            targetName=None
            ):
        
        newData = {
            name: {
                "initial": "",
                "states": {},
                "type": "parallel",
                "onDone": [
                ],
            }
        }

        if targetName:
            newData[name]["onDone"] = {"target": targetName, "actions": []}
        baseMachine["states"].update(newData)

    
if __name__ == "__main__":
    xstateJSONElement = XstateJSONElement()
    xstateJSONElement.initMainMachine("supplypaper", "start", "Name1111", "end")

    xstateJSONElement.singleMessageMachine(xstateJSONElement.mainMachine, "Name1111", "Name2222")
    xstateJSONElement.singleMessageMachine(xstateJSONElement.mainMachine, "Name2222", "eeeee")
    xstateJSONElement.DMNMachine(xstateJSONElement.mainMachine, "eeeee", ["result1", "result2", "result3"],"Gateway_111")

    xstateJSONElement.ExclusiveGatewayMachine(
        xstateJSONElement.mainMachine,
        [
            {"targetName": "aaaaa", "condition": "eeeee_result1==1"},
            {"targetName": "Name2222", "condition": "eeeee_result1==2"},
            {"targetName": "Gateway_222", "condition": "eeeee_result1==3"},
        ],
        "Gateway_111",
    )
    xstateJSONElement.EventGatewayMachine(
        xstateJSONElement.mainMachine,
        [
            {"targetName": "Name1111", "event": "event1"},
            {"targetName": "Name2222", "event": "event2"},
            {"targetName": "Gateway_111", "event": "event3"},
            {"targetName": "aaaaa", "event": "event3"},
        ],
        "Gateway_222",
    )
    xstateJSONElement.MutiTaskLoopMachine(xstateJSONElement.mainMachine, "aaaaa", 2, "eeeee_result1==4", True, "bbbbb",{"name":"dsjhfjka","max":3,"firstTime":True,"participantName":"mutiparticipant1"})
    xstateJSONElement.MutiTaskLoopMachine(xstateJSONElement.mainMachine, "bbbbb", 2, None, False, "ddddd")
    xstateJSONElement.MutiParticipantMachine(xstateJSONElement.mainMachine,"ddddd", 2, "mutiparticipant3", True, "kkkkk")
    xstateJSONElement.MutiParticipantMachine(xstateJSONElement.mainMachine,"kkkkk", 2, "mutiparticipant3",False, "lllll")
    xstateJSONElement.MutiTaskPallelMachine(xstateJSONElement.mainMachine,"lllll", 3, False, "qqqqq")
    xstateJSONElement.MutiTaskPallelMachine(xstateJSONElement.mainMachine,"qqqqq", 3, False, "end",{"name":"dsjhfjka","max":3,"participantName":"mutiparticipant3"})

    with open('output.txt', 'w', encoding='utf-8') as file:
        # 保存 mainMachine 的 JSON 内容
        file.write(json.dumps(xstateJSONElement.mainMachine, indent=4, ensure_ascii=False))
        file.write(",\n")  # 添加换行符

        # 保存 additionalContent 的 JSON 内容，去掉引号
        additional_content = json.dumps(xstateJSONElement.additionalContent, indent=4, ensure_ascii=False)
        # additional_content_no_quotes = additional_content.replace('"', "").replace("\\", "")
        file.write(additional_content)