'use strict';
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');

class FlowWorkload extends WorkloadModuleBase {

  async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
    await super.initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext);
    this.localTxIndex = 0;
  }

  async submitTransaction() {
    const tokenId = `${this.workerIndex}-${this.localTxIndex}-5`;
    this.localTxIndex += 1;

    const channel = this.roundArguments.channel;
    const contractId = this.roundArguments.contractId;

    await this.sutAdapter.sendRequests({
      channel,
      contractId,
      contractFunction: 'MintWithTokenURI',
      contractArguments: [tokenId, 'www.googel.com', '0'], // instanceID 如果不是 0，改成真实的
      invokerIdentity: 'user1' // 按 networks.yaml 的名字改
    });
  }
}

module.exports.createWorkloadModule = () => new FlowWorkload();
