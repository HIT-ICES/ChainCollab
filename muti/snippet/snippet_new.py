import json


data = {
    "context": {
        
    },
    "id": "",
    "initial": "",
    "states": {
        
    },
}

def initMachine(json_data,id,initmachine):
    json_data["id"]=id
    json_data["initial"]=initmachine

def singleMessageMachine(json_data,messageName, targetName):
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
            "onDone": {"target": targetName, "actions": []},
        }
    }

    json_data["states"].update(newData)



def parallelGatewayMachine(json_data):

    #TODO：主要是要识别出并行网关层级关系，并拼装这个层级关系，
    #Gateway_0onpe6x---Gateway_1fbifca
    #    transport order forwarding
    #        mem2_participant1
    #        mem3_participant1
    #        mem1_participant1
    #    supply order forwarding



    #最后类似于这样。lock不用管，后面会写一个函数统一处理
     
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

def mutiTaskMachine(json_data):
    pass

def DMNMachine(json_data):
    pass

def SetMachineFirstTime(json_data):
    pass




initMachine(data,"supplypaper","Name1111")
singleMessageMachine(data, "Name1111", "Name2222")
singleMessageMachine(data, "Name2222", "Name3333")

print(json.dumps(data, indent=4, ensure_ascii=False))
