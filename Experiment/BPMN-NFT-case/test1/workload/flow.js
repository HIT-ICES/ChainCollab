'use strict';

const { WorkloadModuleBase } = require('@hyperledger/caliper-core');

class FlowWorkload extends WorkloadModuleBase {

    async submitTransaction() {

        // 每个 submitTransaction 对应一个流程实例
        const instanceId =
            `${this.roundArguments.instancePrefix}-${this.txIndex}`;

        const channel = this.roundArguments.channel;
        const contractId = this.roundArguments.contractId;

        // ========== Step 1 ==========
        // start：UserA 调用，发事件
        await this.sutAdapter.sendRequests({
            channel,
            contractId, 
            contractFunction: 'Activity_0tux0cj',
            contractArguments: ["0"],
            invokerIdentity: 'user1'
        });

        
    }
}

module.exports.createWorkloadModule = () => {
    return new FlowWorkload();
};
