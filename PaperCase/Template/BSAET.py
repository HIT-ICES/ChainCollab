import json
from typing import List

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

    def initMainMachine(self,id, startEventName,targetName,endEventNameList):
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
        for endEventName in endEventNameList:
            self.mainMachine["states"].update({
                endEventName: {
                    "type": "final",
                }
            })
        
    def initGlobal(self,variables):
        for key in variables:
            self.mainMachine["context"].update({key: None})
            self.additionalContent["actions"].update(
                {
                "set_MessageGlobal_{key}".format(
                        key=key
                    ): "assign({{{key}: ({{context, event}}) => event.values.{key}}})".format(
                        key=key
                    )
                }
            )

        
        


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
                    "guard": name + "__" + target["targetName"],
                    "actions": [],
                }
            )
            cond = target["condition"].replace('"', "'") if target["condition"] else None
            self.additionalContent["guards"].update(
                {
                    name
                    + "__"
                    + target[
                        "targetName"
                    ]: "({{context, event}},params) => {{return {condition};}}".format(
                        condition="context." + cond if cond else "true"
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


    def singleMessageMachine(self,baseMachine, name, targetName=None,GlobalVariables=None):
        newData = {
            name: {
                "initial": "enable",
                "states": {
                    "enable": {
                        "on": {"Send_"+name: [{"target": "wait for confirm", "actions": []}]}
                    },
                    "wait for confirm": {
                        "on": {"Confirm_"+name: [{"target": "done", "actions": []}]}
                    },
                    "done": {"type": "final"},
                },
            }
        }
        if GlobalVariables:
            newData[name]["states"]["wait for confirm"]["on"]["Confirm_"+name][0]["actions"].append({"type": "set_MessageGlobal_{key}".format(key=key) for key in GlobalVariables})
        if targetName:
            newData[name]["onDone"] = {"target": targetName, "actions": []}

        baseMachine["states"].update(newData)


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
                        "guard": name + "_NotLoopMax",
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
                    "guard": name + "_LoopConditionMeet",
                    "actions": [],
                }
            )


        if isMutiParticipant:
            self.ChooseMutiParticipantMachine(newData[name], name, MutiParticipantParam["max"], MutiParticipantParam["participantName"])
            # self.MutiParticipantMachine(newData[name], MutiParticipantParam["name"], MutiParticipantParam["max"], MutiParticipantParam["participantName"],MutiParticipantParam["firstTime"])
            newData[name]["initial"] = name

        else:
            self.singleMessageMachine(newData[name], name)
            newData[name]["initial"] = name

        LoopAdd = {
            name
            + "_LoopAdd": "assign({{{name}_loop: ({{context}}) => context.{name}_loop + 1}})".format(
                name=name
            ),
        }
        ConditionLoopNotMax = {
            name
            + "_NotLoopMax": "({{context, event}},params) => {{return context.{name}_loop !== context.{name}_loopMax;}}".format(
                name=name
            ),
        }
        ConditionLoopMax = {
            name
            + "_LoopMax": "({{context, event}},params) => {{return context.{name}_loop === context.{name}_loopMax;}}".format(
                name=name
            ),
        }

        # TODO:这边==问题，先不管了。
        LoopConditionMeet = {
            name
            + "_LoopConditionMeet": "({{context, event}},params) => {{return context.{expression};}}".format(
                expression=LoopConditionExpression
            ),
        }

        baseMachine["context"].update({name + "_loop": 1, name + "_loopMax": loopMax})

        self.additionalContent["actions"].update(LoopAdd)
        self.additionalContent["guards"].update(ConditionLoopNotMax)
        self.additionalContent["guards"].update(ConditionLoopMax)

        if not LoopConditionExpression:
            LoopConditionMeet = {
                name
                + "_LoopConditionMeet": "({context, event},params) => {return false;}",
            }
        self.additionalContent["guards"].update(LoopConditionMeet)

        if targetName:
            newData[name]["onDone"].append(
                {
                    "target": targetName,
                    "guard": name + "_LoopMax",
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
            for index in range(0,ParallelNum):
                self.ChooseMutiParticipantMachine(newData[name], name+"_"+str(index), MutiParticipantParam["max"],MutiParticipantParam["participantName"])
                # self.MutiParticipantMachine(newData[name], name+"_instance_"+str(index), MutiParticipantParam["max"],MutiParticipantParam["participantName"])
            newData[name]["initial"] = name+"_0"

        else:
            for index in range(0,ParallelNum):
                self.singleMessageMachine(newData[name], name+"_"+str(index))
            newData[name]["initial"] = name+"_0"



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
                                        {"type":name + "_setDMNResult" + "_{key}".format(key=key)}
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
        baseMachine["context"].update({key: None for key in DMNOutput})

        # 如果有多个DMNresult
        self.additionalContent["actions"].update(
            {
                name
                + "_setDMNResult_{key}".format(
                    key=key
                ): "assign({{{key}: ({{context, event}}) => event.values.{key}}})".format(
                    name=name, key=key
                )
                for key in DMNOutput
            }
        )
    


    #这里的participantName为muti的，single的不用给
    def ChooseMutiParticipantMachine(self,baseMachine,name, max, participantName,targetName=None):
        newData = {
            name: {
                "initial": "pending",
                "states": {
                    "pending": {
                        "always": [
                            {
                                "target": name+"_firstTime",
                                "guard": participantName+"_isNotLocked",
                                "actions": [
                                    {
                                        "type": "lock_"+participantName,
                                    }
                                ],
                            },
                            {
                                "target": name,
                                "guard": participantName+"_isLocked",
                                "actions": [],
                            },
                        ],
                    },
                    "done": {
                        "type": "final",
                    },
                    
                },
                "onDone": [],
            },
        }
        self.mainMachine["context"].update({participantName+"_locked": False})
        self.additionalContent["guards"].update(
            {
                participantName+"_isLocked": "({context, event},params) => {return context."+participantName+"_locked;}",
            }
        )
        self.additionalContent["guards"].update(
            {
                participantName+"_isNotLocked": "({context, event},params) => {return !context."+participantName+"_locked;}",
            }
        )
        self.additionalContent["actions"].update(
            {
                "lock_"+participantName: "assign({"+participantName+"_locked:true})",
            }
        )
        
        #为了ondone,加一个done
        self.MutiParticipantMachine(newData[name],name, max, participantName,False,"done")
        self.MutiParticipantMachine(newData[name],name, max, participantName,True,"done")

        if targetName:
            self.SetOndone(newData[name], targetName)
        baseMachine["states"].update(newData)

        



    def MutiParticipantMachine(self,baseMachine,name, max, participantName,firstTime=False, targetName=None):

        newData = {
            name+"_firstTime" if firstTime else name: {
                "initial": "",
                "states": {},
                "onDone": [],
            },
        }

        machineDict = {}


        if firstTime:
            for index in range(0, max):
                self.mainMachine["context"].update({participantName+"_machine_" + str(index): False})
                self.additionalContent["guards"].update(
                    {
                        "active_"+participantName+"_machine_" + str(index): "({context, event},params) => {return context."+participantName+"_machine_" + str(index)+";}",
                    }
                )
                self.additionalContent["guards"].update(
                    {
                        "inactive_"+participantName+"_machine_" + str(index): "({context, event},params) => {return !context."+participantName+"_machine_" + str(index)+";}",
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
                            "Send_"+name+"_"+str(index): [
                                {
                                "target": "wait for confirm",
                                "actions": [],
                                },
                            ],
                            },
                        },
                        "wait for confirm": {
                            "on": {
                            "Confirm_"+name+"_"+str(index): [
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
            newData[name+"_firstTime"]["states"].update(
                {
                    "unlocked": {
                        "states": machineDict,
                        "on": {
                            "advance_"+name: [
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
            newData[name+"_firstTime"]["states"].update({"locked": {"type": "final"}})
            newData[name+"_firstTime"]["initial"]="unlocked"

        else:
            for index in range(0, max):
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
                                            "guard": "active_" + participantName + "_machine_" + str(index),
                                            "actions": [],
                                        },
                                        {
                                            "target": "locked_done",
                                            "guard": "inactive_"
                                            + participantName
                                            + "_machine_"
                                            + str(index),
                                            "actions": [],
                                        },
                                    ],
                                },
                                "enable": {
                                    "on": {
                                        "Send_"+name+"_"+str(index): [
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
                                        "Confirm_"+name+"_"+str(index): [
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
            newData[name]["initial"]="machine_0"

        if targetName:
            self.SetOndone(newData[name+"_firstTime"] if firstTime else newData[name], targetName)

        baseMachine["states"].update(newData)

