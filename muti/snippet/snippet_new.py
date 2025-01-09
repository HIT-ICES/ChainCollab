import json
from typing import List


# TODO:1.并行网关-->并行状态机   2.事件网关 得特殊处理，和ondone冲突。后面应该还是要统一处理ondone和这个网关。 3.排他条件网关=ondone+condition
       



#主状态机
mainMachine = {
    "context": {},
    "id": "",
    "initial": "",
    "states": {},
}


#actions：DMN结果，激活mutiparticipant,MutiTask循环自增 等函数
#guards：mutiparticipant条件，网关条件，mutiTask跳出条件
additionalContent = {
    "actions": {},
    "services": {},
    "guards": {},
    "delays": {},
  }

def initMachine(id,initmachine):
    mainMachine["id"]=id
    mainMachine["initial"]=initmachine

def singleMessageMachine(baseMachine,messageName, *targetName):
    newData = {
        messageName: {
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
        newData[messageName]["onDone"] = {"target": targetName, "actions": []}

    baseMachine["states"].update(newData)



def parallelGatewayMachine(level):

    #TODO：在parser里解析出层级关系，并基于这个层级关系，递归拼装这个并行网关状态机，
    #Gateway_0onpe6x---Gateway_1fbifca
    #    transport order forwarding
    #        mem2_participant1
    #        mem3_participant1
    #        mem1_participant1
    #    supply order forwarding



    #最后类似于这样。lock不用管，后面会写一个函数统一增强逻辑
     
    '''
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
      },'''
    pass


def MutiTaskLoopMachine(basicMachine,name,targetName,loopMax,LoopConditionExpression,isMutiParticipant,*participants):
    
    newData = {
      name: {
          "initial": "",
          "states": {
          },
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
        newData[name]["onDone"].append({
            "target": targetName,
            "cond": name + "_LoopConditionMeet",
            "actions": [],
        })

    if isMutiParticipant:
        newData[name]["type"] = "parallel"

        # TODO:如果同时是mutiparticiant的情况，则需要动态的拼接
        newData[name]["states"].update({})

        newData[name]["initial"] = participants[0]
    else:
        singleMessageMachine(newData[name],name)
        newData[name]["initial"] = "enable"


    LoopAdd = {
        name + "_LoopAdd": "assign({{{name}_loop: (context) => context.{name}_loop + 1}})".format(name=name),
    }
    ConditionLoopNotMax={
        name + "_NotLoopMax": "(context, event) => {{return context.{name}_loop !== context.{name}_loopMax;}}".format(name=name),
    }
    ConditionLoopMax = {
        name + "_LoopMax": "(context, event) => {{return context.{name}_loop === context.{name}_loopMax;}}".format(name=name),
    }

    #TODO:这边==问题，先不管了。
    LoopConditionMeet = {
        name + "_LoopConditionMeet": "(context, event) => {{return context.{expression};}}".format(expression=LoopConditionExpression),
    }
  
    basicMachine["states"].update(newData)
    basicMachine["context"].update({name+"_loop": 1, name+"_loopMax": loopMax})

    additionalContent["actions"].update(LoopAdd)
    additionalContent["guards"].update(ConditionLoopNotMax)
    additionalContent["guards"].update(ConditionLoopMax)
    if LoopConditionExpression:
        additionalContent["guards"].update(LoopConditionMeet)
    



def MutiTaskPallelMachine():
    pass

    

def DMNMachine(basicMachine,name,DMNOutput:List[str]):
    newData = {
        "priority decison": {
        "initial": "enable",
        "states": {
          "enable": {
            "on": {
              "next": [
                {
                  "target": "done",
                  "actions": [name+"_setDMNResult"+"_{key}".format(key=key) for key in DMNOutput],
                },
              ],
            },
          },
          "done": {
            "type": "final",
          },
        },
        "onDone": [
        
        ],
      },
    }

    basicMachine["states"].update(newData)

    #TODO:context可以扩展为更多类型
    #把DMNOutput数组写入到context中
    basicMachine["context"].update({name+"_"+key: None for key in DMNOutput})

    #如果有多个DMNresult
    additionalContent["actions"].update({
        name+"_setDMNResult_{key}".format(key=key): "assign({{{name}_{key}: (context,event) => event.values.{key}}})".format(name=name,key=key) for key in DMNOutput
    })
  

def SetMachineFirstTime():
    pass




initMachine("supplypaper","Name1111")

singleMessageMachine(mainMachine,"Name1111", "Name2222")
singleMessageMachine(mainMachine,"Name2222", "Name3333")

MutiTaskLoopMachine(mainMachine,"cccc","bbbbb",5,"result==1",True,"mem1_participant1","mem2_participant1","mem3_participant1")

MutiTaskLoopMachine(mainMachine,"ddddd","bbbbb",5,None,False)

DMNMachine(mainMachine,"eeeee",["result1","result2","result3"])





print(json.dumps(mainMachine, indent=4, ensure_ascii=False))
#这一部分，函数需要去除引号
print(json.dumps(additionalContent, indent=4,ensure_ascii=False).replace("\"",""))
