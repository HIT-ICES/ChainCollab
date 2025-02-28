const { Contract } = require('fabric-contract-api');
const { createMachine, interpret } = require('xstate');

class StateMachineContract extends Contract {
    async executeStateMachine(ctx, machineDescriptionStr, snapshotStr, context, eventStr) {
        try {
            const machineDescription = JSON.parse(machineDescriptionStr);
            const snapshot = JSON.parse(snapshotStr);
            const event = JSON.parse(eventStr);
    
            const machine = createMachine(machineDescription);
    
            const service = interpret(machine).start(snapshot);

            const res = service.send(event);
    
            const changed = res.changed;
            const newSnapshot = service.getSnapshot();
            service.stop();
    
            return JSON.stringify({
                snapshot: newSnapshot,
                changed: changed
            });
        } catch (error) {
            throw new Error(`Error executing state machine: ${error.message}`);
        }
    }

    async getAllElementState(ctx, machineDescriptionStr, snapshotStr) {
        // recongnize all element with their status, and output
    }

    async createInitState(ctx, machineDescriptionStr) {
        try {
            const machineDescription = JSON.parse(machineDescriptionStr);

            const machine = createMachine(machineDescription);
            const service = interpret(machine).start();

            const initSnapshot = service.getSnapshot();
            service.stop();

            return JSON.stringify(initSnapshot);
        } catch (error) {
            throw new Error(`Error creating initial state: ${error.message}`);
        }
    }

}

module.exports = StateMachineContract;