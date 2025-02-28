const { json } = require('express');
const { createMachine, createActor, setup, initialTransition, transition, assign } = require('xstate'); // 使用 CommonJS 语法导入 xstate

const stateMachine = {
  initial: 'idle',
  context: ({ input }) => {
    console.log(input)
    return {
      username: input.username ? input.username : "default",
      password: input.password ? input.password : "default",
      error: null
    }
  },
  states: {
    idle: {
      on: {
        LOGIN: {
          target: 'loading',
          cond: 'isFormValid', // 检查表单是否有效
          actions: 'updateCredentials' // 清除之前的错误信息
        }
      }
    },
    loading: {
      entry: 'logLoading', // 进入 loading 状态时记录日志
      on: {
        RESOLVE: 'success',
        REJECT: {
          target: 'failure',
          actions: 'logFailure' // 记录登录失败
        }
      }
    },
    success: {
      entry: 'logSuccess', // 进入 success 状态时记录日志
      type: 'final' // 最终状态
    },
    failure: {
      on: {
        RETRY: {
          target: 'idle',
          actions: 'clearError' // 重试时清除错误信息
        }
      }
    }
  }
}

// assign({ finalPriority: (context, event) => event.values.finalPriority })


// const actions = {
//   updateCredentials: assign(({ context, event }) => {
//     return {
//       username: event.username,
//       password: event.password
//     }
//   }),
//   clearError: (context) => {
//     context.error = null;
//   },
//   logSuccess: (context) => {
//     console.log('登录成功！用户名:', context.context.username);
//   },
//   logFailure: (context, event) => {
//     console.log('登录失败！错误信息:', context.error);
//   },
//   logLoading: () => {
//     console.log('正在登录...');
//   }
// }


const fs = require('fs');
fs.promises.readFile('./actions.json', 'utf8').then(
  (value) => {
    const actionsContent = JSON.parse(value).actions;
    const guardsContent = JSON.parse(value).guards
    actions = {}
    guards = {}
    for (const key in actionsContent) {
      actions[key] = eval(actionsContent[key]);
    }
    for (const key in guardsContent) {
      guards[key] = eval(guardsContent[key]);
    }

    console.log(actions)
    console.log(guards)

    const loginMachine = createMachine(
      stateMachine,
      {
        actions: actions,
        guards: guards,
      }
    )

    // console.log(stateMachineDescription)

    const actor = createActor(loginMachine, {
      input: {
        username: "",
        password: ""
      }
    })
    actor.start();

    console.log(actor.getSnapshot().value)

    actor.send({
      type: 'LOGIN',
      username: 'admin',
      password: '123456'
    });

    console.log(actor.getSnapshot().value, actor.getSnapshot().context)

    const tempSnapshot = actor.getPersistedSnapshot()

    console.log(tempSnapshot)

    actor.stop()


    // // from 断点

    const newActor = createActor(loginMachine, {
      snapshot: tempSnapshot,
    })

    // snapshot 优先级 比 input高

    newActor.start()

    console.log(newActor.getSnapshot().value, newActor.getSnapshot().context)

    newActor.send({ type: "RESOLVE" })

    console.log(newActor.getSnapshot().value, newActor.getSnapshot().context)

  }
);




