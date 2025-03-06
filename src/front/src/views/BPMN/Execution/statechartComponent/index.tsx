import { createMachine, assign, createActor } from "xstate";
import { createBrowserInspector } from "@statelyai/inspect";


const StatechartInspect = ({ machineContent, addtionalContent, snapshot}) => {
  const inspector  = createBrowserInspector();
  const machineContentObject = JSON.parse(machineContent);
  const actionsContent = JSON.parse(addtionalContent).actions;
  const guardsContent = JSON.parse(addtionalContent).guards
  const actions = {}
  const guards = {}

  for (const key in actionsContent) {
    // 使用 Function 构造函数从字符串创建函数
    actions[key] = new Function(...Object.keys(assign), actionsContent[key]);
  }

  for (const key in guardsContent) {
    guards[key] = new Function(...Object.keys(assign), guardsContent[key]);
  }

  const machine = createMachine(machineContentObject,{
    actions: actions,
    guards: guards
  });


  const actor = createActor(machine, {
    inspect: inspector.inspect,
    snapshot: snapshot
  });
  actor.start();
  actor.stop();

	return (
    <div >
    </div>
	);
};

export default StatechartInspect;