async ExecuteStateMachine(ctx, machineDescriptionStr, additionalContentStr, snapshotStr, eventStr) {
	const machineDescription = JSON.parse(machineDescriptionStr);
	const additionalContent = JSON.parse(additionalContentStr);
	const snapshot = JSON.parse(snapshotStr);
	const event = JSON.parse(eventStr);

	const actionsContent = additionalContent.actions;
	const guardsContent = additionalContent.guards;
	for (const key in actionsContent) {
		actionsContent[key] = eval(actionsContent[key]);
	}
	for (const key in guardsContent) {
		guardsContent[key] = eval(guardsContent[key]);
	}
	const BPMNMachione = createMachine(
		machineDescription,
		{
			actions: actionsContent,
			guards: guardsContent,
		}
	)
	const actor = createActor(BPMNMachione, {
		snapshot: snapshot
	})
	actor.start()
	actor.send(event);
	const newSnapshot = actor.getPersistedSnapshot();
	const changed = JSON.stringify(newSnapshot) !== snapshotStr;
	return JSON.stringify({
		snapshot: JSON.stringify(newSnapshot),
		changed: changed
	});

	
}