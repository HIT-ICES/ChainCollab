const express = require("express");
const bodyParser = require("body-parser");
const cors = require("cors"); // 引入 CORS 中间件
const { createMachine, interpret, assign } = require("xstate");



//使用v4版本的xstate



const app = express();
app.use(cors());
app.use(bodyParser.json());



app.post("/transition", (req, res) => {
	const { machineDescription,additionalContent, serializedSnapshot, event } = req.body;


	const actions = additionalContent.actions;
	const guards = additionalContent.guards;

	for (const key in actions) {
  		actions[key] = eval(actions[key]);
	}	
	for (const key in guards) {
		guards[key] = eval(guards[key]);
  	}
	additionalContent.actions=actions;
	additionalContent.guards=guards;

	console.log(additionalContent)
	console.log(machineDescription)

	try {
			/*
		const machine = createMachine(
			{
			context: {
				context1: "aaa",
			},
			id: "Untitled",
			initial: "First State",
			states: {
				"First State": {
				on: {
					event1: [
					{
						target: "Second State",
						actions: [
						{
							type: "aaa",
						},
						],
					},
					],
				},
				},
				"Second State": {
				always: {
					target: "New state 1",
					cond: "guard1",
					actions: [],
				},
				},
				"New state 1": {},
			},
			predictableActionArguments: true,
			preserveActionOrder: true,
			},
			{
			actions: {
				aaa: assign({
				context1: (context, event) => event.values.value1,
				}),
			},
			services: {},
			guards: {
				guard1: (context, event) => {
				return context.context1 === "bbb";
				},
			},
			delays: {},
			},
		);
		*/
		
		const machine = createMachine(machineDescription,additionalContent);


		const service = interpret(machine).onTransition((state) => {
		console.log(`当前状态: ${state.value}`);
		console.log(`上下文:`, state.context);
		});


		service.start();
		service.send({ type: "event1", values: { value1: "bbb" } }); 
		service.stop();
				


		/*
		const snapshot = serializedSnapshot ? JSON.parse(serializedSnapshot) : {};
		const actor = createActor(machine, {
			snapshot: snapshot,
		});
		actor.start();
		actor.send({ type: event });
		actor.stop();
		const newSnapshot = actor.getPersistedSnapshot();
		const newSerializedSnapshot = JSON.stringify(newSnapshot);
		console.log(newSerializedSnapshot)
		res.json({ newSerializedSnapshot });

		*/
	} catch (error) {
		console.error("Error processing state machine:", error.message);
		res.status(400).json({ error: error.message });
	}
});

// 启动服务器
const PORT = 3000;
app.listen(PORT, () => {
	console.log(`State Machine API is running on http://localhost:${PORT}`);
});
