import "./styles.css";
import React from "react";
import ReactDOM from "react-dom";
import { createMachine, assign } from "xstate";
import { useMachine } from "@xstate/react";
import { inspect } from "@xstate/inspect";
import { interpret } from 'xstate/lib/interpreter';

inspect({
  url: "https://statecharts.io/inspect",
  iframe: false,
});

export const machine = createMachine(
  {
    context: {
      mem1_p1: false,
      mem2_p1: false,
      mem3_p1: false,
      confirmation1_loop: 1,
      confirmation1_loopMax: 3,
      finalPriority: "",
    },
    id: "supplypaper",
    initial: "Goods Order Request",
    states: {
      "Goods Order Request": {
        initial: "enable",
        states: {
          enable: {
            on: {
              "next1-1": [
                {
                  target: "wait for confirm",
                  actions: [],
                },
              ],
            },
          },
          "wait for confirm": {
            on: {
              "next1-2": [
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
          target: "Supply Order Request",
          actions: [],
        },
      },
      "Supply Order Request": {
        initial: "enable",
        states: {
          enable: {
            on: {
              "next2-1": [
                {
                  target: "wait for confirm",
                  actions: [],
                },
              ],
            },
          },
          "wait for confirm": {
            on: {
              "next2-2": [
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
          target: "Gateway_0onpe6x---Gateway_1fbifca",
          actions: [],
        },
      },
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
      },
      "report details": {
        initial: "mem2_participant1",
        states: {
          mem2_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem2_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem2_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-2-2": [
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
                  "next3-2-3": [
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
          mem1_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem1_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem1_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-1-2": [
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
                  "next3-1-3": [
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
          mem3_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem3_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem3_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-3-2": [
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
                  "next3-3-3": [
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
          target: "details provision",
          actions: [],
        },
      },
      "details provision": {
        initial: "mem2_participant1",
        states: {
          mem2_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem2_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem2_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-2-2": [
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
                  "next3-2-3": [
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
          mem1_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem1_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem1_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-1-2": [
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
                  "next3-1-3": [
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
          mem3_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem3_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem3_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-3-2": [
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
                  "next3-3-3": [
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
          target: "waybill",
          actions: [],
        },
      },
      waybill: {
        initial: "mem2_participant1",
        states: {
          mem2_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem2_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem2_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-2-2": [
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
                  "next3-2-3": [
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
          mem1_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem1_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem1_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-1-2": [
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
                  "next3-1-3": [
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
          mem3_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem3_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem3_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-3-2": [
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
                  "next3-3-3": [
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
          target: "priority decison",
          actions: [],
        },
      },
      "priority decison": {
        initial: "enable",
        states: {
          enable: {
            on: {
              next: [
                {
                  target: "done",
                  actions: ["setResult"],
                },
              ],
            },
          },
          done: {
            type: "final",
          },
        },
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
      },
      confirmation2: {
        initial: "mem2_participant1",
        states: {
          mem2_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem2_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem2_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-2-2": [
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
                  "next3-2-3": [
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
          mem1_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem1_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem1_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-1-2": [
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
                  "next3-1-3": [
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
          mem3_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem3_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem3_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-3-2": [
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
                  "next3-3-3": [
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
          target: "supplies delivery info",
          actions: [],
        },
      },
      confirmation3: {
        initial: "mem2_participant1",
        states: {
          mem2_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem2_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem2_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-2-2": [
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
                  "next3-2-3": [
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
          mem1_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem1_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem1_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-1-2": [
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
                  "next3-1-3": [
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
          mem3_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem3_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem3_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-3-2": [
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
                  "next3-3-3": [
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
          target: "supplies delivery info",
          actions: [],
        },
      },
      confirmation4: {
        initial: "mem2_participant1",
        states: {
          mem2_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem2_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem2_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-2-2": [
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
                  "next3-2-3": [
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
          mem1_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem1_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem1_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-1-2": [
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
                  "next3-1-3": [
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
          mem3_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem3_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem3_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-3-2": [
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
                  "next3-3-3": [
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
          target: "supplies delivery info",
          actions: [],
        },
      },
      confirmation1: {
        initial: "mem2_participant1",
        states: {
          mem2_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem2_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem2_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-2-2": [
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
                  "next3-2-3": [
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
          mem1_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem1_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem1_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-1-2": [
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
                  "next3-1-3": [
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
          mem3_participant1: {
            initial: "disable",
            states: {
              disable: {
                always: [
                  {
                    target: "enable",
                    cond: "active_mem3_p1",
                    actions: [],
                  },
                  {
                    target: "locked_done",
                    cond: "inactive_mem3_p1",
                    actions: [],
                  },
                ],
              },
              enable: {
                on: {
                  "next3-3-2": [
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
                  "next3-3-3": [
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
        onDone: [
          {
            target: "confirmation1",
            cond: "NotLoopMax",
            actions: [
              {
                type: "LoopAdd",
              },
            ],
          },
          {
            target: "supplies delivery info",
            cond: "LoopMax",
            actions: [],
          },
        ],
      },
      "supplies delivery info": {
        initial: "enable",
        states: {
          enable: {
            on: {
              next: [
                {
                  target: "wait for confirm",
                  actions: [],
                },
              ],
            },
          },
          "wait for confirm": {
            on: {
              next: [
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
          target: "goods delivery confirmation",
          actions: [],
        },
      },
      "goods delivery confirmation": {
        initial: "enable",
        states: {
          enable: {
            on: {
              next: [
                {
                  target: "wait for confirm",
                  actions: [],
                },
              ],
            },
          },
          "wait for confirm": {
            on: {
              next: [
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
          target: "finish",
          actions: [],
        },
      },
      finish: {
        type: "final",
      },
    },
    predictableActionArguments: true,
    preserveActionOrder: true,
  },
  {
    actions: {
      setResult: assign({
        finalPriority: (context, event) => event.value1,
      }),
      activate_mem1_participant1: assign({
        mem1_p1: () => true,
      }),
      activate_mem2_participant1: assign({
        mem2_p1: () => true,
      }),
      activate_mem3_participant1: assign({
        mem3_p1: () => true,
      }),
      LoopAdd: assign({
        confirmation1_loop: (context) => context.confirmation1_loop + 1,
      }),
    },
    services: {},
    guards: {
      active_mem1_p1: (context, event) => {
        return context.mem1_p1 === true;
      },
      active_mem2_p1: (context, event) => {
        return context.mem2_p1 === true;
      },
      active_mem3_p1: (context, event) => {
        return context.mem3_p1 === true;
      },
      finalPriorityLow: (context, event) => {
        return context.finalPriority === "Low";
      },
      finalPriorityHigh: (context, event) => {
        // Add your guard code here
        return context.finalPriority === "High";
      },
      finalPriorityMedium: (context, event) => {
        return context.finalPriority === "Medium";
      },
      finalPriorityVeryLow: (context, event) => {
        return context.finalPriority === "VeryLow";
      },
      inactive_mem3_p1: (context, event) => {
        return context.mem3_p1 === false;
      },
      inactive_mem2_p1: (context, event) => {
        return context.mem2_p1 === false;
      },
      inactive_mem1_p1: (context, event) => {
        return context.mem1_p1 === false;
      },
      NotLoopMax: (context, event) => {
        return context.confirmation1_loop !== context.confirmation1_loopMax;
      },
      LoopMax: (context, event) => {
        return context.confirmation1_loop === context.confirmation1_loopMax;
      },
    },
    delays: {},
  }
);

function App() {
  //const [state1, send] = useMachine(machine, { devTools: true });

  const service1 = interpret(machine)
  .onEvent(event => {
    console.log('监听到事件:', event);
  })
  .start();



  
  const service2 = interpret(machine2,{ devTools: true }).start();
  while(true){
    service2.send(event1)
  }
  

  
  

  //const snapshot = { 
  //  value:{
  //    "Goods Order Request":"wait for confirm"
  //  }
  //}

  //service.send(snapshot);

  /*service.state = {
    "actions": [],
    "activities": {},
    "meta": {},
    "events": [],
    "value": {
        "Goods Order Request": "wait for confirm"
    },
    "context": {
        "mem1_p1": false,
        "mem2_p1": false,
        "mem3_p1": false,
        "confirmation1_loop": 1,
        "confirmation1_loopMax": 3,
        "finalPriority": ""
    },
    "_event": {
        "name": "xstate.init",
        "data": {
            "type": "xstate.init"
        },
        "$$type": "scxml",
        "type": "external"
    },
    "_sessionid": "x:0",
    "event": {
        "type": "xstate.init"
    },
    "children": {},
    "done": false,
    "tags": []
}*/

  return (
    <div className="App">
      <button onClick={() => send("next1-1")}>next1-1</button>
      <button onClick={() => send("next1-2")}>next1-2</button>
      <button onClick={() => send("next2-1")}>next2-1</button>
      <button onClick={() => send("next2-2")}>next2-2</button>

      <button onClick={() => send("next1-1-1")}>next1-1-1</button>
      <button onClick={() => send("next1-1-2")}>next1-1-2</button>
      <button onClick={() => send("next2-1-1")}>next2-1-1</button>
      <button onClick={() => send("next2-1-2")}>next2-1-2</button>
      <button onClick={() => send("next2-2-1")}>next2-2-1</button>
      <button onClick={() => send("next2-3-1")}>next2-3-1</button>
      <button onClick={() => send("advance")}>advance</button>

      <button onClick={() => send("next3-1-2")}>next3-1-2</button>
      <button onClick={() => send("next3-1-3")}>next3-1-3</button>

      <button onClick={() => send("next3-1-2")}>next3-1-2</button>
      <button onClick={() => send("next3-1-3")}>next3-1-3</button>

      <button onClick={() => send("next3-1-2")}>next3-1-2</button>
      <button onClick={() => send("next3-1-3")}>next3-1-3</button>

      <button onClick={() => send({ type: "next", value1: "VeryLow" })}>nextWithParam</button>

      <button onClick={() => send("next3-1-2")}>next3-1-2</button>
      <button onClick={() => send("next3-1-3")}>next3-1-3</button>
      <button onClick={() => send("next3-1-2")}>next3-1-2</button>
      <button onClick={() => send("next3-1-3")}>next3-1-3</button>
      <button onClick={() => send("next3-1-2")}>next3-1-2</button>
      <button onClick={() => send("next3-1-3")}>next3-1-3</button>

      <button onClick={() => send("next")}>next</button>
      <button onClick={() => send("next")}>next</button>
      <button onClick={() => send("next")}>next</button>
      <button onClick={() => send("next")}>next</button>
    </div>
  );
}

const rootElement = document.getElementById("root");
ReactDOM.render(<App />, rootElement);
