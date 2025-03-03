//import { createMachine, assign } from "xstate";
import { createMachine, assign, createActor } from "xstate";
// import { inspect } from "@xstate/inspect";
import { createBrowserInspector } from "@statelyai/inspect";

//inspect({
//  url: "https://statecharts.io/inspect",
//  iframe: false,
//});
const {inspect} = createBrowserInspector({
  iframe: document.getElementById('inspector-iframe'),
});

export const machine = createMachine();


const statechartInspect = (props) => {

  const actor = createActor(machine, {
    inspect,
    // ... other actor options
  });
  actor.start();

	return (
		<iframe id="inspector-iframe"></iframe>
	);
};

export default statechartInspect;