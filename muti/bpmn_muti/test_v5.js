import { createMachine } from "xstate";
export const machine = createMachine(
  {
    context: {
      finalPriority: null,
      Message_0d2xte5_loop: 1,
      Message_0i5t589_loop: 1,
      Message_0d2xte5_loopMax: 3,
      Message_0i5t589_loopMax: 2,
      Participant_19j1e3o_locked: false,
      Participant_19j1e3o_machine_1: false,
      Participant_19j1e3o_machine_2: false,
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
      Gateway_0onpe6x_TO_Gateway_1fbifca: {
        states: {
          "Gateway_0onpe6x to Gateway_1fbifca path 0": {
            initial: "Message_0cba4t6",
            states: {
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
              done: {
                type: "final",
              },
            },
          },
          "Gateway_0onpe6x to Gateway_1fbifca path 1": {
            initial: "Message_0pm90nx",
            states: {
              Message_0pm90nx: {
                initial: "pending",
                states: {
                  pending: {
                    always: [
                      {
                        target: "Message_0pm90nx_firstTime",
                        guard: "Participant_19j1e3o_isNotLocked",
                        actions: [
                          {
                            type: "lock_Participant_19j1e3o",
                          },
                        ],
                      },
                      {
                        target: "Message_0pm90nx",
                        guard: "Participant_19j1e3o_isLocked",
                        actions: [],
                      },
                    ],
                  },
                  Message_0pm90nx_firstTime: {
                    initial: "unlocked",
                    states: {
                      unlocked: {
                        states: {
                          machine_1: {
                            initial: "enable",
                            states: {
                              enable: {
                                on: {
                                  Send_Message_0pm90nx1: [
                                    {
                                      target: "wait for confirm",
                                      actions: [],
                                    },
                                  ],
                                },
                              },
                              "wait for confirm": {
                                on: {
                                  Confirm_Message_0pm90nx1: [
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
                                  Send_Message_0pm90nx2: [
                                    {
                                      target: "wait for confirm",
                                      actions: [],
                                    },
                                  ],
                                },
                              },
                              "wait for confirm": {
                                on: {
                                  Confirm_Message_0pm90nx2: [
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
                  Message_0pm90nx: {
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
                              Send_Message_0pm90nx1: [
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
                              Confirm_Message_0pm90nx1: [
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
                              Send_Message_0pm90nx2: [
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
                              Confirm_Message_0pm90nx2: [
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
                      target: "done",
                      actions: [],
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
              done: {
                type: "final",
              },
            },
          },
        },
        type: "parallel",
        onDone: {
          target: "Message_0rwz1km",
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
                          Send_Message_0rwz1km1: [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      "wait for confirm": {
                        on: {
                          Confirm_Message_0rwz1km1: [
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
                          Send_Message_0rwz1km2: [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      "wait for confirm": {
                        on: {
                          Confirm_Message_0rwz1km2: [
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
                      Send_Message_0rwz1km1: [
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
                      Confirm_Message_0rwz1km1: [
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
                      Send_Message_0rwz1km2: [
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
                      Confirm_Message_0rwz1km2: [
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
              target: "done",
              actions: [],
            },
          },
          done: {
            type: "final",
          },
        },
        onDone: {
          target: "Message_0i5t589",
          actions: [],
        },
      },
      Message_0i5t589: {
        initial: "Message_0i5t589_instance",
        states: {
          Message_0i5t589_instance: {
            initial: "pending",
            states: {
              pending: {
                always: [
                  {
                    target: "Message_0i5t589_instance_firstTime",
                    guard: "Participant_19j1e3o_isNotLocked",
                    actions: [
                      {
                        type: "lock_Participant_19j1e3o",
                      },
                    ],
                  },
                  {
                    target: "Message_0i5t589_instance",
                    guard: "Participant_19j1e3o_isLocked",
                    actions: [],
                  },
                ],
              },
              Message_0i5t589_instance_firstTime: {
                initial: "unlocked",
                states: {
                  unlocked: {
                    states: {
                      machine_1: {
                        initial: "enable",
                        states: {
                          enable: {
                            on: {
                              Send_Message_0i5t589_instance1: [
                                {
                                  target: "wait for confirm",
                                  actions: [],
                                },
                              ],
                            },
                          },
                          "wait for confirm": {
                            on: {
                              Confirm_Message_0i5t589_instance1: [
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
                              Send_Message_0i5t589_instance2: [
                                {
                                  target: "wait for confirm",
                                  actions: [],
                                },
                              ],
                            },
                          },
                          "wait for confirm": {
                            on: {
                              Confirm_Message_0i5t589_instance2: [
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
              Message_0i5t589_instance: {
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
                          Send_Message_0i5t589_instance1: [
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
                          Confirm_Message_0i5t589_instance1: [
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
                          Send_Message_0i5t589_instance2: [
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
                          Confirm_Message_0i5t589_instance2: [
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
                  target: "done",
                  actions: [],
                },
              },
              done: {
                type: "final",
              },
            },
          },
        },
        type: "parallel",
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
      },
      Message_0oi7nug: {
        initial: "Message_0oi7nug_instance_1",
        states: {
          Message_0oi7nug_instance_1: {
            initial: "enable",
            states: {
              enable: {
                on: {
                  Send_Message_0oi7nug_instance_1: [
                    {
                      target: "wait for confirm",
                      actions: [],
                    },
                  ],
                },
              },
              "wait for confirm": {
                on: {
                  Confirm_Message_0oi7nug_instance_1: [
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
          Message_0oi7nug_instance_2: {
            initial: "enable",
            states: {
              enable: {
                on: {
                  Send_Message_0oi7nug_instance_2: [
                    {
                      target: "wait for confirm",
                      actions: [],
                    },
                  ],
                },
              },
              "wait for confirm": {
                on: {
                  Confirm_Message_0oi7nug_instance_2: [
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
          Message_0oi7nug_instance_3: {
            initial: "enable",
            states: {
              enable: {
                on: {
                  Send_Message_0oi7nug_instance_3: [
                    {
                      target: "wait for confirm",
                      actions: [],
                    },
                  ],
                },
              },
              "wait for confirm": {
                on: {
                  Confirm_Message_0oi7nug_instance_3: [
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
                          Send_Message_1oxmq1k1: [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      "wait for confirm": {
                        on: {
                          Confirm_Message_1oxmq1k1: [
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
                          Send_Message_1oxmq1k2: [
                            {
                              target: "wait for confirm",
                              actions: [],
                            },
                          ],
                        },
                      },
                      "wait for confirm": {
                        on: {
                          Confirm_Message_1oxmq1k2: [
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
                      Send_Message_1oxmq1k1: [
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
                      Confirm_Message_1oxmq1k1: [
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
                      Send_Message_1oxmq1k2: [
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
                      Confirm_Message_1oxmq1k2: [
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
              target: "done",
              actions: [],
            },
          },
          done: {
            type: "final",
          },
        },
        onDone: {
          target: "Gateway_1cr0nma",
          actions: [],
        },
      },
      Message_0d2xte5: {
        initial: "Message_0d2xte5_instance",
        states: {
          Message_0d2xte5_instance: {
            initial: "pending",
            states: {
              pending: {
                always: [
                  {
                    target: "Message_0d2xte5_instance_firstTime",
                    guard: "Participant_19j1e3o_isNotLocked",
                    actions: [
                      {
                        type: "lock_Participant_19j1e3o",
                      },
                    ],
                  },
                  {
                    target: "Message_0d2xte5_instance",
                    guard: "Participant_19j1e3o_isLocked",
                    actions: [],
                  },
                ],
              },
              Message_0d2xte5_instance_firstTime: {
                initial: "unlocked",
                states: {
                  unlocked: {
                    states: {
                      machine_1: {
                        initial: "enable",
                        states: {
                          enable: {
                            on: {
                              Send_Message_0d2xte5_instance1: [
                                {
                                  target: "wait for confirm",
                                  actions: [],
                                },
                              ],
                            },
                          },
                          "wait for confirm": {
                            on: {
                              Confirm_Message_0d2xte5_instance1: [
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
                              Send_Message_0d2xte5_instance2: [
                                {
                                  target: "wait for confirm",
                                  actions: [],
                                },
                              ],
                            },
                          },
                          "wait for confirm": {
                            on: {
                              Confirm_Message_0d2xte5_instance2: [
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
              Message_0d2xte5_instance: {
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
                          Send_Message_0d2xte5_instance1: [
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
                          Confirm_Message_0d2xte5_instance1: [
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
                          Send_Message_0d2xte5_instance2: [
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
                          Confirm_Message_0d2xte5_instance2: [
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
                  target: "done",
                  actions: [],
                },
              },
              done: {
                type: "final",
              },
            },
          },
        },
        type: "parallel",
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
      },
      Gateway_1cr0nma: {
        always: {
          target: "Event_13pbqdz",
          guard: "Gateway_1cr0nma__Event_13pbqdz",
          actions: [],
        },
      },
      Event_13pbqdz: {
        type: "final",
      },
      Message_1ni5gbl: {
        initial: "enable",
        states: {
          enable: {
            on: {
              Send_Message_1ni5gbl: [
                {
                  target: "wait for confirm",
                  actions: [],
                },
              ],
            },
          },
          "wait for confirm": {
            on: {
              Confirm_Message_1ni5gbl: [
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
    },
  },
  {
    actions: {
      activate_Participant_19j1e3o_machine_1: ({ context, event }) => {},
      activate_Participant_19j1e3o_machine_2: ({ context, event }) => {},
      lock_Participant_19j1e3o: ({ context, event }) => {},
      Message_0i5t589_LoopAdd: ({ context, event }) => {},
      set_MessageGlobal_finalPriority: ({ context, event }) => {},
      Message_0d2xte5_LoopAdd: ({ context, event }) => {},
    },
    actors: {},
    guards: {
      Participant_19j1e3o_isNotLocked: ({ context, event }, params) => {
        return false;
      },
      Participant_19j1e3o_isLocked: ({ context, event }, params) => {
        return false;
      },
      active_Participant_19j1e3o_machine_1: ({ context, event }, params) => {
        return false;
      },
      inactive_Participant_19j1e3o_machine_1: ({ context, event }, params) => {
        return false;
      },
      active_Participant_19j1e3o_machine_2: ({ context, event }, params) => {
        return false;
      },
      inactive_Participant_19j1e3o_machine_2: ({ context, event }, params) => {
        return false;
      },
      Message_0i5t589_NotLoopMax: ({ context, event }, params) => {
        return false;
      },
      Message_0i5t589_LoopConditionMeet: ({ context, event }, params) => {
        return false;
      },
      Message_0i5t589_LoopMax: ({ context, event }, params) => {
        return false;
      },
      Gateway_0ep8cuh__Message_1oxmq1k: ({ context, event }, params) => {
        return false;
      },
      Gateway_0ep8cuh__Message_0d2xte5: ({ context, event }, params) => {
        return false;
      },
      Gateway_1cr0nma__Event_13pbqdz: ({ context, event }, params) => {
        return false;
      },
      Message_0d2xte5_NotLoopMax: ({ context, event }, params) => {
        return false;
      },
      Message_0d2xte5_LoopMax: ({ context, event }, params) => {
        return false;
      },
    },
    delays: {},
  },
);