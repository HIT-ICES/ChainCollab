const { Contract } = require('fabric-contract-api');
const { createMachine, createActor, assign } = require('xstate');

class StateMachineContract extends Contract {
    async GetDefaultSnapshot(ctx, machineDescriptionStr, additionalContentStr) {
        try {
            const machineDescription = JSON.parse(machineDescriptionStr);
            const additionalContent = JSON.parse(additionalContentStr);

            const actionsContent = additionalContent.actions;
            const guardsContent = additionalContent.guards;
            
            const actions = {};
            const guards = {};

            for (const key in actionsContent) {
                actions[key] = eval(actionsContent[key]);
            }
            for (const key in guardsContent) {
                guards[key] = eval(guardsContent[key]);
            }

            const BPMNMachione = createMachine(
                machineDescription,
                {
                    actions: actions,
                    guards: guards,
                }
            )

            const actor = createActor(BPMNMachione, {})
            const snapshot = actor.getPersistedSnapshot();
            return JSON.stringify(snapshot);
        } catch (error) {
            throw new Error(`Error getting default snapshot: ${error.message}`);
        }
    }

    async ExecuteStateMachine(ctx, machineDescriptionStr, additionalContentStr, snapshotStr, eventStr) {
        try {
            const machineDescription = JSON.parse(machineDescriptionStr);
            const additionalContent = JSON.parse(additionalContentStr);

            const actionsContent = additionalContent.actions;
            const guardsContent = additionalContent.guards;
            
            const actions = {};
            const guards = {};

            for (const key in actionsContent) {
                actions[key] = eval(actionsContent[key]);
            }
            for (const key in guardsContent) {
                guards[key] = eval(guardsContent[key]);
            }


            const snapshot = JSON.parse(snapshotStr);

            const event = JSON.parse(eventStr);

            const BPMNMachione = createMachine(
                machineDescription,
                {
                    actions: actions,
                    guards: guards,
                }
            )

            const actor = createActor(BPMNMachione, {
                snapshot: snapshot
            })

            actor.start()
            actor.send(event);

            const newSnapshot = actor.getPersistedSnapshot();

            const changed = newSnapshot !== snapshot;


            return JSON.stringify({
                snapshot: newSnapshot,
                changed: changed
            });
        } catch (error) {
            throw new Error(`Error executing state machine: ${error.message}`);
        }
    }
}

module.exports = StateMachineContract;