//import { createMachine, assign } from "xstate";
import { createMachine, assign, createActor } from "xstate";
// import { inspect } from "@xstate/inspect";
import { createBrowserInspector } from "@statelyai/inspect";

//inspect({
//  url: "https://statecharts.io/inspect",
//  iframe: false,
//});

const { inspect } = createBrowserInspector();

const machine = createMachine(
  {
    context: {
      finalPriority: null,
      Participant_19j1e3o_locked: false,
      Participant_19j1e3o_machine_1: false,
      Participant_19j1e3o_machine_2: false,
      Message_0i5t589_loop: 1,
      Message_0i5t589_loopMax: 2,
      Message_0d2xte5_loop: 1,
      Message_0d2xte5_loopMax: 3,
    },
    id: "NewTest_paper",
    initial: "Event_06sexe6",
    states: {
      Event_06sexe6: {
        always: {
          target: "Message_1wswgqu",
          actions: [],
        },
      },
      Event_13pbqdz: {
        type: "final",
      },
      Message_1wswgqu: {
        initial: "enable",
        states: {
          enable: {
            on: {
              Send_Message_1wswgqu: [
                {
                  target: "wait for confirm",
                  actions: [],
                },
              ],
            },
          },
          "wait for confirm": {
            on: {
              Confirm_Message_1wswgqu: [
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
        onDone: {
          target: "Gateway_0onpe6x_TO_Gateway_1fbifca",
          actions: [],
        },
      },
      Message_0rwz1km: {
        initial: "pending",
        states: {
          pending: {
            always: [
              {
                target: "Message_0rwz1km_firstTime",
                guard: "Participant_19j1e3o_isNotLocked",
                actions: [
                  {
                    type: "lock_Participant_19j1e3o",
                  },
                ],
              },
              {
                target: "Message_0rwz1km",
                guard: "Participant_19j1e3o_isLocked",
                actions: [],
              },
            ],
          },
          done: {
            type: "final",
          },
          Message_0rwz1km: {
            initial: "machine_1",
            states: {
              machine_1: {
                initial: "disable",
                states: {
                  disable: {
                    always: [
                      {
                        target: "enable",
                        guard: "active_Participant_19j1e3o_machine_1",
                        actions: [],
                      },
                      {
                        target: "locked_done",
                        guard: "inactive_Participant_19j1e3o_machine_1",
                        actions: [],
                      },
                    ],
                  },
                  enable: {
                    on: {
                      Send_Message_0rwz1km_1: [
                        {
                          target: "wait for confirm",
                          actions: [],
                        },
                      ],
                    },
                  },
                  locked_done: {
                    type: "final",
                  },
                  "wait for confirm": {
                    on: {
                      Confirm_Message_0rwz1km_1: [
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
              machine_2: {
                initial: "disable",
                states: {
                  disable: {
                    always: [
                      {
                        target: "enable",
                        guard: "active_Participant_19j1e3o_machine_2",
                        actions: [],
                      },
                      {
                        target: "locked_done",
                        guard: "inactive_Participant_19j1e3o_machine_2",
                        actions: [],
                      },
                    ],
                  },
                  enable: {
                    on: {
                      Send_Message_0rwz1km_2: [
                        {
                          target: "wait for confirm",
                          actions: [],
                        },
                      ],
                    },
                  },
                  locked_done: {
                    type: "final",
                  },
                  "wait for confirm": {
                    on: {
                      Confirm_Message_0rwz1km_2: [
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
            onDone: {
              target: "done",
              actions: [],
            },
            type: "parallel",
          },
          Message_0rwz1km_firstTime: {
            initial: "unlocked",
            states: {
              unlocked: {
                states: {
                  machine_1: {
                    initial: "enable",
                    states: {
                      enable: {
                        on: {
                          Send_Message_0rwz1km_1: [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      "wait for confirm": {
                        on: {
                          Confirm_Message_0rwz1km_1: [
                            {
                              target: "done",
                              actions: [],
                            },
                          ],
                        },
                      },
                      done: {
                        entry: {
                          type: "activate_Participant_19j1e3o_machine_1",
                        },
                      },
                    },
                  },
                  machine_2: {
                    initial: "enable",
                    states: {
                      enable: {
                        on: {
                          Send_Message_0rwz1km_2: [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      "wait for confirm": {
                        on: {
                          Confirm_Message_0rwz1km_2: [
                            {
                              target: "done",
                              actions: [],
                            },
                          ],
                        },
                      },
                      done: {
                        entry: {
                          type: "activate_Participant_19j1e3o_machine_2",
                        },
                      },
                    },
                  },
                },
                on: {
                  advance: [
                    {
                      target: "locked",
                      actions: [],
                    },
                  ],
                },
                type: "parallel",
              },
              locked: {
                type: "final",
              },
            },
            onDone: {
              target: "done",
              actions: [],
            },
          },
        },
        onDone: {
          target: "Message_0i5t589",
          actions: [],
        },
      },
      Message_0i5t589: {
        initial: "Message_0i5t589_",
        states: {
          Message_0i5t589: {
            initial: "pending",
            states: {
              pending: {
                always: [
                  {
                    target: "Message_0i5t589_firstTime",
                    guard: "Participant_19j1e3o_isNotLocked",
                    actions: [
                      {
                        type: "lock_Participant_19j1e3o",
                      },
                    ],
                  },
                  {
                    target: "Message_0i5t589",
                    guard: "Participant_19j1e3o_isLocked",
                    actions: [],
                  },
                ],
              },
              done: {
                type: "final",
              },
              Message_0i5t589: {
                initial: "machine_1",
                states: {
                  machine_1: {
                    initial: "disable",
                    states: {
                      disable: {
                        always: [
                          {
                            target: "enable",
                            guard: "active_Participant_19j1e3o_machine_1",
                            actions: [],
                          },
                          {
                            target: "locked_done",
                            guard: "inactive_Participant_19j1e3o_machine_1",
                            actions: [],
                          },
                        ],
                      },
                      enable: {
                        on: {
                          Send_Message_0i5t589_1: [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      locked_done: {
                        type: "final",
                      },
                      "wait for confirm": {
                        on: {
                          Confirm_Message_0i5t589_1: [
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
                  machine_2: {
                    initial: "disable",
                    states: {
                      disable: {
                        always: [
                          {
                            target: "enable",
                            guard: "active_Participant_19j1e3o_machine_2",
                            actions: [],
                          },
                          {
                            target: "locked_done",
                            guard: "inactive_Participant_19j1e3o_machine_2",
                            actions: [],
                          },
                        ],
                      },
                      enable: {
                        on: {
                          Send_Message_0i5t589_2: [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      locked_done: {
                        type: "final",
                      },
                      "wait for confirm": {
                        on: {
                          Confirm_Message_0i5t589_2: [
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
                onDone: {
                  target: "done",
                  actions: [],
                },
                type: "parallel",
              },
              Message_0i5t589_firstTime: {
                initial: "unlocked",
                states: {
                  unlocked: {
                    states: {
                      machine_1: {
                        initial: "enable",
                        states: {
                          enable: {
                            on: {
                              Send_Message_0i5t589_1: [
                                {
                                  target: "wait for confirm",
                                  actions: [],
                                },
                              ],
                            },
                          },
                          "wait for confirm": {
                            on: {
                              Confirm_Message_0i5t589_1: [
                                {
                                  target: "done",
                                  actions: [],
                                },
                              ],
                            },
                          },
                          done: {
                            entry: {
                              type: "activate_Participant_19j1e3o_machine_1",
                            },
                          },
                        },
                      },
                      machine_2: {
                        initial: "enable",
                        states: {
                          enable: {
                            on: {
                              Send_Message_0i5t589_2: [
                                {
                                  target: "wait for confirm",
                                  actions: [],
                                },
                              ],
                            },
                          },
                          "wait for confirm": {
                            on: {
                              Confirm_Message_0i5t589_2: [
                                {
                                  target: "done",
                                  actions: [],
                                },
                              ],
                            },
                          },
                          done: {
                            entry: {
                              type: "activate_Participant_19j1e3o_machine_2",
                            },
                          },
                        },
                      },
                    },
                    on: {
                      advance: [
                        {
                          target: "locked",
                          actions: [],
                        },
                      ],
                    },
                    type: "parallel",
                  },
                  locked: {
                    type: "final",
                  },
                },
                onDone: {
                  target: "done",
                  actions: [],
                },
              },
            },
            onDone: [],
          },
        },
        onDone: [
          {
            target: "Message_0i5t589",
            guard: "Message_0i5t589_NotLoopMax",
            actions: [
              {
                type: "Message_0i5t589_LoopAdd",
              },
            ],
          },
          {
            target: "Message_0oi7nug",
            guard: "Message_0i5t589_LoopConditionMeet",
            actions: [],
          },
          {
            target: "Message_0oi7nug",
            guard: "Message_0i5t589_LoopMax",
            actions: [],
          },
        ],
        type: "parallel",
      },
      Message_0oi7nug: {
        initial: "Message_0oi7nug_1",
        states: {
          Message_0oi7nug_1: {
            initial: "enable",
            states: {
              enable: {
                on: {
                  Send_Message_0oi7nug_1: [
                    {
                      target: "wait for confirm",
                      actions: [],
                    },
                  ],
                },
              },
              "wait for confirm": {
                on: {
                  Confirm_Message_0oi7nug_1: [
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
          Message_0oi7nug_2: {
            initial: "enable",
            states: {
              enable: {
                on: {
                  Send_Message_0oi7nug_2: [
                    {
                      target: "wait for confirm",
                      actions: [],
                    },
                  ],
                },
              },
              "wait for confirm": {
                on: {
                  Confirm_Message_0oi7nug_2: [
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
          Message_0oi7nug_3: {
            initial: "enable",
            states: {
              enable: {
                on: {
                  Send_Message_0oi7nug_3: [
                    {
                      target: "wait for confirm",
                      actions: [],
                    },
                  ],
                },
              },
              "wait for confirm": {
                on: {
                  Confirm_Message_0oi7nug_3: [
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
          target: "Message_1io2g9u",
          actions: [],
        },
      },
      Message_1io2g9u: {
        initial: "enable",
        states: {
          enable: {
            on: {
              Send_Message_1io2g9u: [
                {
                  target: "wait for confirm",
                  actions: [],
                },
              ],
            },
          },
          "wait for confirm": {
            on: {
              Confirm_Message_1io2g9u: [
                {
                  target: "done",
                  actions: [
                    {
                      type: "set_MessageGlobal_finalPriority",
                    },
                  ],
                },
              ],
            },
          },
          done: {
            type: "final",
          },
        },
        onDone: {
          target: "Gateway_0ep8cuh",
          actions: [],
        },
      },
      Gateway_0ep8cuh: {
        always: [
          {
            target: "Message_1oxmq1k",
            guard: "Gateway_0ep8cuh__Message_1oxmq1k",
            actions: [],
          },
          {
            target: "Message_0d2xte5",
            guard: "Gateway_0ep8cuh__Message_0d2xte5",
            actions: [],
          },
        ],
      },
      Message_1oxmq1k: {
        initial: "pending",
        states: {
          pending: {
            always: [
              {
                target: "Message_1oxmq1k_firstTime",
                guard: "Participant_19j1e3o_isNotLocked",
                actions: [
                  {
                    type: "lock_Participant_19j1e3o",
                  },
                ],
              },
              {
                target: "Message_1oxmq1k",
                guard: "Participant_19j1e3o_isLocked",
                actions: [],
              },
            ],
          },
          done: {
            type: "final",
          },
          Message_1oxmq1k: {
            initial: "machine_1",
            states: {
              machine_1: {
                initial: "disable",
                states: {
                  disable: {
                    always: [
                      {
                        target: "enable",
                        guard: "active_Participant_19j1e3o_machine_1",
                        actions: [],
                      },
                      {
                        target: "locked_done",
                        guard: "inactive_Participant_19j1e3o_machine_1",
                        actions: [],
                      },
                    ],
                  },
                  enable: {
                    on: {
                      Send_Message_1oxmq1k_1: [
                        {
                          target: "wait for confirm",
                          actions: [],
                        },
                      ],
                    },
                  },
                  locked_done: {
                    type: "final",
                  },
                  "wait for confirm": {
                    on: {
                      Confirm_Message_1oxmq1k_1: [
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
              machine_2: {
                initial: "disable",
                states: {
                  disable: {
                    always: [
                      {
                        target: "enable",
                        guard: "active_Participant_19j1e3o_machine_2",
                        actions: [],
                      },
                      {
                        target: "locked_done",
                        guard: "inactive_Participant_19j1e3o_machine_2",
                        actions: [],
                      },
                    ],
                  },
                  enable: {
                    on: {
                      Send_Message_1oxmq1k_2: [
                        {
                          target: "wait for confirm",
                          actions: [],
                        },
                      ],
                    },
                  },
                  locked_done: {
                    type: "final",
                  },
                  "wait for confirm": {
                    on: {
                      Confirm_Message_1oxmq1k_2: [
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
            onDone: {
              target: "done",
              actions: [],
            },
            type: "parallel",
          },
          Message_1oxmq1k_firstTime: {
            initial: "unlocked",
            states: {
              unlocked: {
                states: {
                  machine_1: {
                    initial: "enable",
                    states: {
                      enable: {
                        on: {
                          Send_Message_1oxmq1k_1: [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      "wait for confirm": {
                        on: {
                          Confirm_Message_1oxmq1k_1: [
                            {
                              target: "done",
                              actions: [],
                            },
                          ],
                        },
                      },
                      done: {
                        entry: {
                          type: "activate_Participant_19j1e3o_machine_1",
                        },
                      },
                    },
                  },
                  machine_2: {
                    initial: "enable",
                    states: {
                      enable: {
                        on: {
                          Send_Message_1oxmq1k_2: [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      "wait for confirm": {
                        on: {
                          Confirm_Message_1oxmq1k_2: [
                            {
                              target: "done",
                              actions: [],
                            },
                          ],
                        },
                      },
                      done: {
                        entry: {
                          type: "activate_Participant_19j1e3o_machine_2",
                        },
                      },
                    },
                  },
                },
                on: {
                  advance: [
                    {
                      target: "locked",
                      actions: [],
                    },
                  ],
                },
                type: "parallel",
              },
              locked: {
                type: "final",
              },
            },
            onDone: {
              target: "done",
              actions: [],
            },
          },
        },
        onDone: {
          target: "Gateway_1cr0nma",
          actions: [],
        },
      },
      Gateway_1cr0nma: {
        always: [
          {
            target: "Event_13pbqdz",
            guard: "Gateway_1cr0nma__Event_13pbqdz",
            actions: [],
          },
        ],
      },
      Message_0d2xte5: {
        initial: "Message_0d2xte5_",
        states: {
          Message_0d2xte5: {
            initial: "pending",
            states: {
              pending: {
                always: [
                  {
                    target: "Message_0d2xte5_firstTime",
                    guard: "Participant_19j1e3o_isNotLocked",
                    actions: [
                      {
                        type: "lock_Participant_19j1e3o",
                      },
                    ],
                  },
                  {
                    target: "Message_0d2xte5",
                    guard: "Participant_19j1e3o_isLocked",
                    actions: [],
                  },
                ],
              },
              done: {
                type: "final",
              },
              Message_0d2xte5: {
                initial: "machine_1",
                states: {
                  machine_1: {
                    initial: "disable",
                    states: {
                      disable: {
                        always: [
                          {
                            target: "enable",
                            guard: "active_Participant_19j1e3o_machine_1",
                            actions: [],
                          },
                          {
                            target: "locked_done",
                            guard: "inactive_Participant_19j1e3o_machine_1",
                            actions: [],
                          },
                        ],
                      },
                      enable: {
                        on: {
                          Send_Message_0d2xte5_1: [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      locked_done: {
                        type: "final",
                      },
                      "wait for confirm": {
                        on: {
                          Confirm_Message_0d2xte5_1: [
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
                  machine_2: {
                    initial: "disable",
                    states: {
                      disable: {
                        always: [
                          {
                            target: "enable",
                            guard: "active_Participant_19j1e3o_machine_2",
                            actions: [],
                          },
                          {
                            target: "locked_done",
                            guard: "inactive_Participant_19j1e3o_machine_2",
                            actions: [],
                          },
                        ],
                      },
                      enable: {
                        on: {
                          Send_Message_0d2xte5_2: [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      locked_done: {
                        type: "final",
                      },
                      "wait for confirm": {
                        on: {
                          Confirm_Message_0d2xte5_2: [
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
                onDone: {
                  target: "done",
                  actions: [],
                },
                type: "parallel",
              },
              Message_0d2xte5_firstTime: {
                initial: "unlocked",
                states: {
                  unlocked: {
                    states: {
                      machine_1: {
                        initial: "enable",
                        states: {
                          enable: {
                            on: {
                              Send_Message_0d2xte5_1: [
                                {
                                  target: "wait for confirm",
                                  actions: [],
                                },
                              ],
                            },
                          },
                          "wait for confirm": {
                            on: {
                              Confirm_Message_0d2xte5_1: [
                                {
                                  target: "done",
                                  actions: [],
                                },
                              ],
                            },
                          },
                          done: {
                            entry: {
                              type: "activate_Participant_19j1e3o_machine_1",
                            },
                          },
                        },
                      },
                      machine_2: {
                        initial: "enable",
                        states: {
                          enable: {
                            on: {
                              Send_Message_0d2xte5_2: [
                                {
                                  target: "wait for confirm",
                                  actions: [],
                                },
                              ],
                            },
                          },
                          "wait for confirm": {
                            on: {
                              Confirm_Message_0d2xte5_2: [
                                {
                                  target: "done",
                                  actions: [],
                                },
                              ],
                            },
                          },
                          done: {
                            entry: {
                              type: "activate_Participant_19j1e3o_machine_2",
                            },
                          },
                        },
                      },
                    },
                    on: {
                      advance: [
                        {
                          target: "locked",
                          actions: [],
                        },
                      ],
                    },
                    type: "parallel",
                  },
                  locked: {
                    type: "final",
                  },
                },
                onDone: {
                  target: "done",
                  actions: [],
                },
              },
            },
            onDone: [],
          },
        },
        onDone: [
          {
            target: "Message_0d2xte5",
            guard: "Message_0d2xte5_NotLoopMax",
            actions: [
              {
                type: "Message_0d2xte5_LoopAdd",
              },
            ],
          },
          {
            target: "Gateway_1cr0nma",
            guard: "Message_0d2xte5_LoopMax",
            actions: [],
          },
        ],
        type: "parallel",
      },
      Gateway_0onpe6x_TO_Gateway_1fbifca: {
        initial: "",
        states: {
          "Gateway_0onpe6x to Gateway_1fbifca path 0": {
            initial: "Message_0cba4t6",
            states: {
              done: {
                type: "final",
              },
              Message_0cba4t6: {
                initial: "enable",
                states: {
                  enable: {
                    on: {
                      Send_Message_0cba4t6: [
                        {
                          target: "wait for confirm",
                          actions: [],
                        },
                      ],
                    },
                  },
                  "wait for confirm": {
                    on: {
                      Confirm_Message_0cba4t6: [
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
                onDone: {
                  target: "Message_1ip9ryp",
                  actions: [],
                },
              },
              Message_1ip9ryp: {
                initial: "enable",
                states: {
                  enable: {
                    on: {
                      Send_Message_1ip9ryp: [
                        {
                          target: "wait for confirm",
                          actions: [],
                        },
                      ],
                    },
                  },
                  "wait for confirm": {
                    on: {
                      Confirm_Message_1ip9ryp: [
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
                onDone: {
                  target: "done",
                  actions: [],
                },
              },
            },
            onDone: [],
          },
          "Gateway_0onpe6x to Gateway_1fbifca path 1": {
            initial: "Message_0pm90nx",
            states: {
              done: {
                type: "final",
              },
              Message_0pm90nx: {
                initial: "enable",
                states: {
                  enable: {
                    on: {
                      Send_Message_0pm90nx: [
                        {
                          target: "wait for confirm",
                          actions: [],
                        },
                      ],
                    },
                  },
                  "wait for confirm": {
                    on: {
                      Confirm_Message_0pm90nx: [
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
                onDone: {
                  target: "done",
                  actions: [],
                },
              },
            },
            onDone: [],
          },
        },
        onDone: {
          target: "Message_0rwz1km",
          actions: [],
        },
        type: "parallel",
      },
    },
  },
  {
    actions: {
      set_MessageGlobal_finalPriority: assign({
        finalPriority: ({ context, event }) => event.values.finalPriority,
      }),
      lock_Participant_19j1e3o: assign({ Participant_19j1e3o_locked: true }),
      activate_Participant_19j1e3o_machine_1: assign({
        Participant_19j1e3o_machine_1: true,
      }),
      activate_Participant_19j1e3o_machine_2: assign({
        Participant_19j1e3o_machine_2: true,
      }),
      Message_0i5t589_LoopAdd: assign({
        Message_0i5t589_loop: ({ context }) => context.Message_0i5t589_loop + 1,
      }),
      Message_0d2xte5_LoopAdd: assign({
        Message_0d2xte5_loop: ({ context }) => context.Message_0d2xte5_loop + 1,
      }),
    },
    services: {},
    guards: {
      Participant_19j1e3o_isLocked: ({ context, event }, params) => {
        return context.Participant_19j1e3o_locked;
      },
      Participant_19j1e3o_isNotLocked: ({ context, event }, params) => {
        return !context.Participant_19j1e3o_locked;
      },
      active_Participant_19j1e3o_machine_1: ({ context, event }, params) => {
        return context.Participant_19j1e3o_machine_1;
      },
      inactive_Participant_19j1e3o_machine_1: ({ context, event }, params) => {
        return !context.Participant_19j1e3o_machine_1;
      },
      active_Participant_19j1e3o_machine_2: ({ context, event }, params) => {
        return context.Participant_19j1e3o_machine_2;
      },
      inactive_Participant_19j1e3o_machine_2: ({ context, event }, params) => {
        return !context.Participant_19j1e3o_machine_2;
      },
      Message_0i5t589_NotLoopMax: ({ context, event }, params) => {
        return context.Message_0i5t589_loop !== context.Message_0i5t589_loopMax;
      },
      Message_0i5t589_LoopMax: ({ context, event }, params) => {
        return context.Message_0i5t589_loop === context.Message_0i5t589_loopMax;
      },
      Message_0i5t589_LoopConditionMeet: ({ context, event }, params) => {
        return context.true;
      },
      Gateway_0ep8cuh__Message_1oxmq1k: ({ context, event }, params) => {
        return context.finalPriority == "Low";
      },
      Gateway_0ep8cuh__Message_0d2xte5: ({ context, event }, params) => {
        return context.finalPriority == "VeryLow";
      },
      Gateway_1cr0nma__Event_13pbqdz: ({ context, event }, params) => {
        return true;
      },
      Message_0d2xte5_NotLoopMax: ({ context, event }, params) => {
        return context.Message_0d2xte5_loop !== context.Message_0d2xte5_loopMax;
      },
      Message_0d2xte5_LoopMax: ({ context, event }, params) => {
        return context.Message_0d2xte5_loop === context.Message_0d2xte5_loopMax;
      },
    },
    delays: {},
  }
);