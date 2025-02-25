const { createMachine } = require('xstate'); // 使用 CommonJS 语法导入 xstate

// 创建带有子状态机的状态机
const machine = createMachine({
  id: 'trafficLight',
  initial: 'operational',
  states: {
    operational: {
      initial: 'green',
      states: {
        green: {
          on: { TIMER: 'yellow' }
        },
        yellow: {
          on: { TIMER: 'red' }
        },
        red: {
          on: { TIMER: 'green' }
        }
      },
      on: {
        POWER_OUTAGE: 'offline'
      }
    },
    offline: {
      on: {
        POWER_RESTORED: 'operational'
      }
    }
  }
});

// 创建 actor 实例
const actor = createMachine(machine);

const init_snapshot = actor.getPersistedSnapshot();
console.log(typeof(init_snapshot))

// 启动 actor
actor.start();

// 发送事件给 actor
actor.send({type:'TIMER'}); // 从 green -> yellow

// 获取持久化快照
const persistedSnapshot = actor.getPersistedSnapshot();

// 序列化快照
const serializedSnapshot = JSON.stringify(persistedSnapshot);
console.log('Serialized Persisted Snapshot:', serializedSnapshot);

// 反序列化快照
const deserializedSnapshot = JSON.parse(serializedSnapshot);
// 模拟重新加载状态机并导入快照
const newActor = createMachine(machine,{
  snapshot: deserializedSnapshot
});

console.log('Restored Persisted Snapshot:', newActor.getPersistedSnapshot());

// 启动新的 actor
newActor.start();

// 继续发送事件
newActor.send({type:'TIMER'}); // 从 red -> green
newActor.send({type:'POWER_OUTAGE'}); // 从 operational -> offline

// 获取新的持久化快照
const finalPersistedSnapshot = newActor.getPersistedSnapshot();
console.log('Final Persisted Snapshot:', JSON.stringify(finalPersistedSnapshot));
