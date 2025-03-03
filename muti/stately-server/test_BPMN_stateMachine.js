const { json } = require('express');
const { createMachine, createActor, setup, initialTransition, transition, assign } = require('xstate'); // 使用 CommonJS 语法导入 xstate

const fs = require('fs');
const { start } = require('repl');

const global_machine = {
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
}

global_actions = {
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
}

global_guards = {
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
}


const get_default_snapshot = async () => {
    // const mainMachineContent = global_machine
    // const additionalContent = await fs.promises.readFile('./additionalContent.json', 'utf8')

    const mainMachine = global_machine
    const actions = global_actions
    const guards = global_guards
    // const actionsContent = JSON.parse(additionalContent).actions;
    // const guardsContent = JSON.parse(additionalContent).guards
    // const actions = {}
    // const guards = {}

    // for (const key in actionsContent) {
    //     actions[key] = eval(actionsContent[key]);
    // }
    // for (const key in guardsContent) {
    //     guards[key] = eval(guardsContent[key]);
    // }

    const BPMNMachione = createMachine(
        mainMachine,
        {
            actions: actions,
            guards: guards,
        }
    )

    const actor = createActor(BPMNMachione, {})

    actor.start();
    const init_snapshot = actor.getPersistedSnapshot()
    actor.stop()
    return init_snapshot
}


const run_and_save = async (snapshot, event) => {
    // const mainMachineContent = global_machine
    // const additionalContent = await fs.promises.readFile('./additionalContent.json', 'utf8')

    // const mainMachine = global_machine
    // const actionsContent = JSON.parse(additionalContent).actions;
    // const guardsContent = JSON.parse(additionalContent).guards
    // const actions = {}
    // const guards = {}

    const mainMachine = global_machine
    const actions = global_actions
    const guards = global_guards

    // for (const key in actionsContent) {
    //     actions[key] = eval(actionsContent[key]);
    // }
    // for (const key in guardsContent) {
    //     guards[key] = eval(guardsContent[key]);
    // }

    const BPMNMachione = createMachine(
        mainMachine,
        {
            actions: actions,
            guards: guards,
        }
    )

    const actor = createActor(BPMNMachione, {
        snapshot: snapshot,
    })
    actor.start()
    actor.send(event)
    // compare changed or not
    const newSnapshot = actor.getPersistedSnapshot()


    return newSnapshot
}


const events_list = [
    {
        type: 'Send_Message_1wswgqu',
    },
    {
        type: 'Confirm_Message_1wswgqu',
    },
    {
        type: "Send_Message_0cba4t6",
    }
]


const run_events_list = async (snapshot, events_list) => {
    let tempSnapshot = snapshot
    for (const event of events_list) {
        tempSnapshot = await run_and_save(tempSnapshot, event)
        console.log(tempSnapshot)
    }
    return tempSnapshot
}

const recongnize_from_state = (snapshot) => {
    // design a Method to recognize_from value: state, and machine description to a full element description

}


const test_xstate = async () => {
    const init_snapshot = await get_default_snapshot()
    // console.log(init_snapshot)
    run_events_list(init_snapshot, events_list)
}

test_xstate()