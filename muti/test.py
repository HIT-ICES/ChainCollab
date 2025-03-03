import fastapi
import json

import requests


additionalStr = """
{
            "actions": {
                "lock_Participant_17tx0st": "assign({Participant_17tx0st_locked:true})",
                "activate_Participant_17tx0st_machine_1": "assign({Participant_17tx0st_machine_1:true})",
                "activate_Participant_17tx0st_machine_2": "assign({Participant_17tx0st_machine_2:true})",
                "activate_Participant_17tx0st_machine_3": "assign({Participant_17tx0st_machine_3:true})",
                "activate_Participant_17tx0st_machine_4": "assign({Participant_17tx0st_machine_4:true})",
                "activate_Participant_17tx0st_machine_5": "assign({Participant_17tx0st_machine_5:true})",
                "activate_Participant_17tx0st_machine_6": "assign({Participant_17tx0st_machine_6:true})",
                "activate_Participant_17tx0st_machine_7": "assign({Participant_17tx0st_machine_7:true})",
                "activate_Participant_17tx0st_machine_8": "assign({Participant_17tx0st_machine_8:true})",
                "activate_Participant_17tx0st_machine_9": "assign({Participant_17tx0st_machine_9:true})",
                "activate_Participant_17tx0st_machine_10": "assign({Participant_17tx0st_machine_10:true})"
            },
            "services": {},
            "guards": {
                "Participant_17tx0st_isLocked": "({context, event},params) => {return context.Participant_17tx0st_locked;}",
                "Participant_17tx0st_isNotLocked": "({context, event},params) => {return !context.Participant_17tx0st_locked;}",
                "active_Participant_17tx0st_machine_1": "({context, event},params) => {return context.Participant_17tx0st_machine_1;}",
                "inactive_Participant_17tx0st_machine_1": "({context, event},params) => {return !context.Participant_17tx0st_machine_1;}",
                "active_Participant_17tx0st_machine_2": "({context, event},params) => {return context.Participant_17tx0st_machine_2;}",
                "inactive_Participant_17tx0st_machine_2": "({context, event},params) => {return !context.Participant_17tx0st_machine_2;}",
                "active_Participant_17tx0st_machine_3": "({context, event},params) => {return context.Participant_17tx0st_machine_3;}",
                "inactive_Participant_17tx0st_machine_3": "({context, event},params) => {return !context.Participant_17tx0st_machine_3;}",
                "active_Participant_17tx0st_machine_4": "({context, event},params) => {return context.Participant_17tx0st_machine_4;}",
                "inactive_Participant_17tx0st_machine_4": "({context, event},params) => {return !context.Participant_17tx0st_machine_4;}",
                "active_Participant_17tx0st_machine_5": "({context, event},params) => {return context.Participant_17tx0st_machine_5;}",
                "inactive_Participant_17tx0st_machine_5": "({context, event},params) => {return !context.Participant_17tx0st_machine_5;}",
                "active_Participant_17tx0st_machine_6": "({context, event},params) => {return context.Participant_17tx0st_machine_6;}",
                "inactive_Participant_17tx0st_machine_6": "({context, event},params) => {return !context.Participant_17tx0st_machine_6;}",
                "active_Participant_17tx0st_machine_7": "({context, event},params) => {return context.Participant_17tx0st_machine_7;}",
                "inactive_Participant_17tx0st_machine_7": "({context, event},params) => {return !context.Participant_17tx0st_machine_7;}",
                "active_Participant_17tx0st_machine_8": "({context, event},params) => {return context.Participant_17tx0st_machine_8;}",
                "inactive_Participant_17tx0st_machine_8": "({context, event},params) => {return !context.Participant_17tx0st_machine_8;}",
                "active_Participant_17tx0st_machine_9": "({context, event},params) => {return context.Participant_17tx0st_machine_9;}",
                "inactive_Participant_17tx0st_machine_9": "({context, event},params) => {return !context.Participant_17tx0st_machine_9;}",
                "active_Participant_17tx0st_machine_10": "({context, event},params) => {return context.Participant_17tx0st_machine_10;}",
                "inactive_Participant_17tx0st_machine_10": "({context, event},params) => {return !context.Participant_17tx0st_machine_10;}"
            },
            "delays": {}
        }
"""
machineStr = """{
            "context": {
                "Participant_17tx0st_locked": false,
                "Participant_17tx0st_machine_1": false,
                "Participant_17tx0st_machine_2": false,
                "Participant_17tx0st_machine_3": false,
                "Participant_17tx0st_machine_4": false,
                "Participant_17tx0st_machine_5": false,
                "Participant_17tx0st_machine_6": false,
                "Participant_17tx0st_machine_7": false,
                "Participant_17tx0st_machine_8": false,
                "Participant_17tx0st_machine_9": false,
                "Participant_17tx0st_machine_10": false
            },
            "id": "MainMachine",
            "initial": "Event_0ooh8t8",
            "states": {
                "Event_0ooh8t8": {
                    "always": {
                        "target": "Message_0j305jt",
                        "actions": []
                    }
                },
                "Event_1rmj9g7": {
                    "type": "final"
                },
                "Message_0j305jt": {
                    "initial": "pending",
                    "states": {
                        "pending": {
                            "always": [
                                {
                                    "target": "Message_0j305jt_firstTime",
                                    "guard": "Participant_17tx0st_isNotLocked",
                                    "actions": [
                                        {
                                            "type": "lock_Participant_17tx0st"
                                        }
                                    ]
                                },
                                {
                                    "target": "Message_0j305jt",
                                    "guard": "Participant_17tx0st_isLocked",
                                    "actions": []
                                }
                            ]
                        },
                        "done": {
                            "type": "final"
                        },
                        "Message_0j305jt": {
                            "initial": "machine_1",
                            "states": {
                                "machine_1": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_1",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_1",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0j305jt_1": [
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
                                                "Confirm_Message_0j305jt_1": [
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
                                                    "guard": "active_Participant_17tx0st_machine_2",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_2",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0j305jt_2": [
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
                                                "Confirm_Message_0j305jt_2": [
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
                                "machine_3": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_3",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_3",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0j305jt_3": [
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
                                                "Confirm_Message_0j305jt_3": [
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
                                "machine_4": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_4",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_4",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0j305jt_4": [
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
                                                "Confirm_Message_0j305jt_4": [
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
                                "machine_5": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_5",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_5",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0j305jt_5": [
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
                                                "Confirm_Message_0j305jt_5": [
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
                                "machine_6": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_6",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_6",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0j305jt_6": [
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
                                                "Confirm_Message_0j305jt_6": [
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
                                "machine_7": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_7",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_7",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0j305jt_7": [
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
                                                "Confirm_Message_0j305jt_7": [
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
                                "machine_8": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_8",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_8",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0j305jt_8": [
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
                                                "Confirm_Message_0j305jt_8": [
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
                                "machine_9": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_9",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_9",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0j305jt_9": [
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
                                                "Confirm_Message_0j305jt_9": [
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
                                "machine_10": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_10",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_10",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0j305jt_10": [
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
                                                "Confirm_Message_0j305jt_10": [
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
                        "Message_0j305jt_firstTime": {
                            "initial": "unlocked",
                            "states": {
                                "unlocked": {
                                    "states": {
                                        "machine_1": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0j305jt_1": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0j305jt_1": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_1"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_2": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0j305jt_2": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0j305jt_2": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_2"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_3": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0j305jt_3": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0j305jt_3": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_3"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_4": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0j305jt_4": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0j305jt_4": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_4"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_5": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0j305jt_5": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0j305jt_5": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_5"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_6": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0j305jt_6": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0j305jt_6": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_6"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_7": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0j305jt_7": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0j305jt_7": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_7"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_8": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0j305jt_8": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0j305jt_8": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_8"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_9": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0j305jt_9": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0j305jt_9": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_9"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_10": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0j305jt_10": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0j305jt_10": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_10"
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
                        "target": "Message_0ip1epl",
                        "actions": []
                    }
                },
                "Message_0ip1epl": {
                    "initial": "pending",
                    "states": {
                        "pending": {
                            "always": [
                                {
                                    "target": "Message_0ip1epl_firstTime",
                                    "guard": "Participant_17tx0st_isNotLocked",
                                    "actions": [
                                        {
                                            "type": "lock_Participant_17tx0st"
                                        }
                                    ]
                                },
                                {
                                    "target": "Message_0ip1epl",
                                    "guard": "Participant_17tx0st_isLocked",
                                    "actions": []
                                }
                            ]
                        },
                        "done": {
                            "type": "final"
                        },
                        "Message_0ip1epl": {
                            "initial": "machine_1",
                            "states": {
                                "machine_1": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_1",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_1",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0ip1epl_1": [
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
                                                "Confirm_Message_0ip1epl_1": [
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
                                                    "guard": "active_Participant_17tx0st_machine_2",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_2",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0ip1epl_2": [
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
                                                "Confirm_Message_0ip1epl_2": [
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
                                "machine_3": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_3",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_3",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0ip1epl_3": [
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
                                                "Confirm_Message_0ip1epl_3": [
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
                                "machine_4": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_4",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_4",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0ip1epl_4": [
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
                                                "Confirm_Message_0ip1epl_4": [
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
                                "machine_5": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_5",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_5",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0ip1epl_5": [
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
                                                "Confirm_Message_0ip1epl_5": [
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
                                "machine_6": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_6",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_6",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0ip1epl_6": [
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
                                                "Confirm_Message_0ip1epl_6": [
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
                                "machine_7": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_7",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_7",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0ip1epl_7": [
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
                                                "Confirm_Message_0ip1epl_7": [
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
                                "machine_8": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_8",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_8",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0ip1epl_8": [
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
                                                "Confirm_Message_0ip1epl_8": [
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
                                "machine_9": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_9",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_9",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0ip1epl_9": [
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
                                                "Confirm_Message_0ip1epl_9": [
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
                                "machine_10": {
                                    "initial": "disable",
                                    "states": {
                                        "disable": {
                                            "always": [
                                                {
                                                    "target": "enable",
                                                    "guard": "active_Participant_17tx0st_machine_10",
                                                    "actions": []
                                                },
                                                {
                                                    "target": "locked_done",
                                                    "guard": "inactive_Participant_17tx0st_machine_10",
                                                    "actions": []
                                                }
                                            ]
                                        },
                                        "enable": {
                                            "on": {
                                                "Send_Message_0ip1epl_10": [
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
                                                "Confirm_Message_0ip1epl_10": [
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
                        "Message_0ip1epl_firstTime": {
                            "initial": "unlocked",
                            "states": {
                                "unlocked": {
                                    "states": {
                                        "machine_1": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0ip1epl_1": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0ip1epl_1": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_1"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_2": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0ip1epl_2": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0ip1epl_2": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_2"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_3": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0ip1epl_3": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0ip1epl_3": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_3"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_4": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0ip1epl_4": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0ip1epl_4": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_4"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_5": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0ip1epl_5": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0ip1epl_5": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_5"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_6": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0ip1epl_6": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0ip1epl_6": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_6"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_7": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0ip1epl_7": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0ip1epl_7": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_7"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_8": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0ip1epl_8": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0ip1epl_8": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_8"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_9": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0ip1epl_9": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0ip1epl_9": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_9"
                                                    }
                                                }
                                            }
                                        },
                                        "machine_10": {
                                            "initial": "enable",
                                            "states": {
                                                "enable": {
                                                    "on": {
                                                        "Send_Message_0ip1epl_10": [
                                                            {
                                                                "target": "wait for confirm",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "wait for confirm": {
                                                    "on": {
                                                        "Confirm_Message_0ip1epl_10": [
                                                            {
                                                                "target": "done",
                                                                "actions": []
                                                            }
                                                        ]
                                                    }
                                                },
                                                "done": {
                                                    "entry": {
                                                        "type": "activate_Participant_17tx0st_machine_10"
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
                        "target": "Event_1rmj9g7",
                        "actions": []
                    }
                }
            }
        }"""

res = requests.post(
    "http://127.0.0.1:5001/api/v1/namespaces/default/apis/StateChartEngine5/query/get_default_snapshot",
    json={
        "input": {
            "additionalContentStr": additionalStr,
            "machineDescriptionStr": machineStr,
        }
    },
)
print("get_default_snapshot", res.text)

snapshot = res.text
res = requests.post(
    "http://127.0.0.1:5001/api/v1/namespaces/default/apis/StateChartEngine5/query/executeStateMachine",
    json={
        "input": {
            "additionalContentStr": additionalStr,
            "machineDescriptionStr": machineStr,
            "snapshotStr":snapshot,
            "eventStr": "{}"
        }
    },
)
print("--------------------------------")
print(res.text)