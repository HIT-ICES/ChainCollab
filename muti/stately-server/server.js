const express = require("express");
const bodyParser = require("body-parser");
const cors = require("cors"); // 引入 CORS 中间件
const { createMachine, createActor } = require("xstate");

const app = express();

app.use(cors());

app.use(bodyParser.json());

app.post("/transition", (req, res) => {
	const { machineDescription, serializedSnapshot, event } = req.body;

	try {
		const machine = createMachine(machineDescription);
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
