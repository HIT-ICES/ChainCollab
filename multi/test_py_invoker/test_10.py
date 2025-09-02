additionalStr = """
{
            "actions": {
                "set_MessageGlobal_finalPriority": "assign({finalPriority: ({context, event}) => event.values.finalPriority})",
                "lock_Participant_19j1e3o": "assign({Participant_19j1e3o_locked:true})",
                "activate_Participant_19j1e3o_machine_1": "assign({Participant_19j1e3o_machine_1:true})",
                "activate_Participant_19j1e3o_machine_2": "assign({Participant_19j1e3o_machine_2:true})",
                "Message_0i5t589_LoopAdd": "assign({Message_0i5t589_loop: ({context}) => context.Message_0i5t589_loop + 1})",
                "Message_0d2xte5_LoopAdd": "assign({Message_0d2xte5_loop: ({context}) => context.Message_0d2xte5_loop + 1})"
            },
            "services": {},
            "guards": {
                "Participant_19j1e3o_isLocked": "({context, event},params) => {return context.Participant_19j1e3o_locked;}",
                "Participant_19j1e3o_isNotLocked": "({context, event},params) => {return !context.Participant_19j1e3o_locked;}",
                "active_Participant_19j1e3o_machine_1": "({context, event},params) => {return context.Participant_19j1e3o_machine_1;}",
                "inactive_Participant_19j1e3o_machine_1": "({context, event},params) => {return !context.Participant_19j1e3o_machine_1;}",
                "active_Participant_19j1e3o_machine_2": "({context, event},params) => {return context.Participant_19j1e3o_machine_2;}",
                "inactive_Participant_19j1e3o_machine_2": "({context, event},params) => {return !context.Participant_19j1e3o_machine_2;}",
                "Message_0i5t589_NotLoopMax": "({context, event},params) => {return context.Message_0i5t589_loop !== context.Message_0i5t589_loopMax;}",
                "Message_0i5t589_LoopMax": "({context, event},params) => {return context.Message_0i5t589_loop === context.Message_0i5t589_loopMax;}",
                "Message_0i5t589_LoopConditionMeet": "({context, event},params) => {return context.true;}",
                "Gateway_0ep8cuh__Message_1oxmq1k": "({context, event},params) => {return context.finalPriority==\"Low\";}", // 不要使用\", 直接使用 ' 单引号,避免json格式冲突
                "Gateway_0ep8cuh__Message_1oxmq1k": "({context, event},params) => {return context.finalPriority=='Low';}",
                "Gateway_0ep8cuh__Message_0d2xte5": "({context, event},params) => {return context.finalPriority==\"VeryLow\";}",
                "Gateway_1cr0nma__Event_13pbqdz": "({context, event},params) => {return true;}",
                "Message_0d2xte5_NotLoopMax": "({context, event},params) => {return context.Message_0d2xte5_loop !== context.Message_0d2xte5_loopMax;}",
                "Message_0d2xte5_LoopMax": "({context, event},params) => {return context.Message_0d2xte5_loop === context.Message_0d2xte5_loopMax;}"
            },
            "delays": {}
        }
"""
machineStr = """{
    "context": {
        "finalPriority": null,
        "Participant_19j1e3o_locked": false,
        "Participant_19j1e3o_machine_1": false,
        "Participant_19j1e3o_machine_2": false,
        "Message_0i5t589_loop": 1,
        "Message_0i5t589_loopMax": 2,
        "Message_0d2xte5_loop": 1,
        "Message_0d2xte5_loopMax": 3
    },
    "id": "MainMachine",
    "initial": "Event_06sexe6",
    "states": {
        "Event_06sexe6": {
            "always": {
                "target": "Message_1wswgqu",
                "actions": []
            }
        },
        "Event_13pbqdz": {
            "type": "final"
        },
        "Message_1wswgqu": {
            "initial": "enable",
            "states": {
                "enable": {
                    "on": {
                        "Send_Message_1wswgqu": [
                            {
                                "target": "wait for confirm",
                                "actions": []
                            }
                        ]
                    }
                },
                "wait for confirm": {
                    "on": {
                        "Confirm_Message_1wswgqu": [
                            {
                                "target": "done",
                                "actions": []
                            }
                        ]
                    }
                },
                "done": {
                    "type": "final"
                }
            },
            "onDone": {
                "target": "Gateway_0onpe6x_TO_Gateway_1fbifca",
                "actions": []
            }
        },
        "Message_0rwz1km": {
            "initial": "pending",
            "states": {
                "pending": {
                    "always": [
                        {
                            "target": "Message_0rwz1km_firstTime",
                            "guard": "Participant_19j1e3o_isNotLocked",
                            "actions": [
                                {
                                    "type": "lock_Participant_19j1e3o"
                                }
                            ]
                        },
                        {
                            "target": "Message_0rwz1km",
                            "guard": "Participant_19j1e3o_isLocked",
                            "actions": []
                        }
                    ]
                },
                "done": {
                    "type": "final"
                },
                "Message_0rwz1km": {
                    "initial": "machine_1",
                    "states": {
                        "machine_1": {
                            "initial": "disable",
                            "states": {
                                "disable": {
                                    "always": [
                                        {
                                            "target": "enable",
                                            "guard": "active_Participant_19j1e3o_machine_1",
                                            "actions": []
                                        },
                                        {
                                            "target": "locked_done",
                                            "guard": "inactive_Participant_19j1e3o_machine_1",
                                            "actions": []
                                        }
                                    ]
                                },
                                "enable": {
                                    "on": {
                                        "Send_Message_0rwz1km_1": [
                                            {
                                                "target": "wait for confirm",
                                                "actions": []
                                            }
                                        ]
                                    }
                                },
                                "locked_done": {
                                    "type": "final"
                                },
                                "wait for confirm": {
                                    "on": {
                                        "Confirm_Message_0rwz1km_1": [
                                            {
                                                "target": "done",
                                                "actions": []
                                            }
                                        ]
                                    }
                                },
                                "done": {
                                    "type": "final"
                                }
                            }
                        },
                        "machine_2": {
                            "initial": "disable",
                            "states": {
                                "disable": {
                                    "always": [
                                        {
                                            "target": "enable",
                                            "guard": "active_Participant_19j1e3o_machine_2",
                                            "actions": []
                                        },
                                        {
                                            "target": "locked_done",
                                            "guard": "inactive_Participant_19j1e3o_machine_2",
                                            "actions": []
                                        }
                                    ]
                                },
                                "enable": {
                                    "on": {
                                        "Send_Message_0rwz1km_2": [
                                            {
                                                "target": "wait for confirm",
                                                "actions": []
                                            }
                                        ]
                                    }
                                },
                                "locked_done": {
                                    "type": "final"
                                },
                                "wait for confirm": {
                                    "on": {
                                        "Confirm_Message_0rwz1km_2": [
                                            {
                                                "target": "done",
                                                "actions": []
                                            }
                                        ]
                                    }
                                },
                                "done": {
                                    "type": "final"
                                }
                            }
                        }
                    },
                    "onDone": {
                        "target": "done",
                        "actions": []
                    },
                    "type": "parallel"
                },
                "Message_0rwz1km_firstTime": {
                    "initial": "unlocked",
                    "states": {
                        "unlocked": {
                            "states": {
                                "machine_1": {
                                    "initial": "enable",
                                    "states": {
                                        "enable": {
                                            "on": {
                                                "Send_Message_0rwz1km_1": [
                                                    {
                                                        "target": "wait for confirm",
                                                        "actions": []
                                                    }
                                                ]
                                            }
                                        },
                                        "wait for confirm": {
                                            "on": {
                                                "Confirm_Message_0rwz1km_1": [
                                                    {
                                                        "target": "done",
                                                        "actions": []
                                                    }
                                                ]
                                            }
                                        },
                                        "done": {
                                            "entry": {
                                                "type": "activate_Participant_19j1e3o_machine_1"
                                            }
                                        }
                                    }
                                },
                                "machine_2": {
                                    "initial": "enable",
                                    "states": {
                                        "enable": {
                                            "on": {
                                                "Send_Message_0rwz1km_2": [
                                                    {
                                                        "target": "wait for confirm",
                                                        "actions": []
                                                    }
                                                ]
                                            }
                                        },
                                        "wait for confirm": {
                                            "on": {
                                                "Confirm_Message_0rwz1km_2": [
                                                    {
                                                        "target": "done",
                                                        "actions": []
                                                    }
                                                ]
                                            }
                                        },
                                        "done": {
                                            "entry": {
                                                "type": "activate_Participant_19j1e3o_machine_2"
                                            }
                                        }
                                    }
                                }
                            },
                            "on": {
                                "advance": [
                                    {
                                        "target": "locked",
                                        "actions": []
                                    }
                                ]
                            },
                            "type": "parallel"
                        },
                        "locked": {
                            "type": "final"
                        }
                    },
                    "onDone": {
                        "target": "done",
                        "actions": []
                    }
                }
            },
            "onDone": {
                "target": "Message_0i5t589",
                "actions": []
            }
        }"""
