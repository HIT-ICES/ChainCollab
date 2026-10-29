/* Local EVM regression for generated message confirmation, not a deployed experiment.
 * Requires solc, ethers and ganache on NODE_PATH.
 * node message_confirmation.evm.cjs <generated MessageConfirmation.sol> <report.json>
 */
const fs = require('node:fs');
const assert = require('node:assert/strict');
const solc = require('solc');
const { ethers } = require('ethers');
const ganache = require('ganache');

async function main() {
  const [sourcePath, reportPath] = process.argv.slice(2);
  assert(sourcePath && reportPath, 'Supply a generated Solidity file and report path');
  const identitySource = `pragma solidity ^0.8.0;
contract TestIdentityRegistry {
 mapping(address => string) private orgs;
 function setOrg(address who, string calldata org) external { orgs[who] = org; }
 function getIdentityOrg(address who) external view returns (string memory) { return orgs[who]; }
}`;
  const output = JSON.parse(solc.compile(JSON.stringify({
    language: 'Solidity',
    sources: { 'workflow.sol': { content: fs.readFileSync(sourcePath, 'utf8') }, 'identity.sol': { content: identitySource } },
    settings: { optimizer: { enabled: true, runs: 200 }, evmVersion: 'shanghai', outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object'] } } }
  })));
  const errors = (output.errors || []).filter(e => e.severity === 'error');
  assert.equal(errors.length, 0, errors.map(e => e.formattedMessage).join('\n'));
  const chain = ganache.provider({ logging: { quiet: true }, chain: { hardfork: 'shanghai' }, wallet: { totalAccounts: 5 } });
  const provider = new ethers.BrowserProvider(chain);
  provider.pollingInterval = 10;
  const signers = await Promise.all([0, 1, 2, 3, 4].map(i => provider.getSigner(i)));
  const [owner, sender, receiver, outsider, multiReceiver] = signers;
  const addresses = await Promise.all(signers.map(s => s.getAddress()));
  const checks = [];
  async function reverted(label, call, reason) {
    await assert.rejects(call, error => String(error).includes(reason));
    checks.push(label);
  }
  async function tx(call) { return await (await call).wait(); }
  try {
    const identityArtifact = output.contracts['identity.sol'].TestIdentityRegistry;
    const identity = await new ethers.ContractFactory(identityArtifact.abi, identityArtifact.evm.bytecode.object, owner).deploy();
    await identity.waitForDeployment();
    await tx(identity.setOrg(addresses[4], 'receiver-org'));
    await tx(identity.setOrg(addresses[3], 'other-org'));
    const artifact = output.contracts['workflow.sol'].MessageConfirmation;
    const contract = await new ethers.ContractFactory(artifact.abi, artifact.evm.bytecode.object, owner).deploy(ethers.ZeroAddress);
    await contract.waitForDeployment();
    await tx(contract.initLedger());
    const params = {
      identityContractAddress: await identity.getAddress(), dmnLiteAddress: ethers.ZeroAddress,
      dmnEvalUrl: '', enforceBusinessRuleCaller: false,
      Sender_account: addresses[1], Sender_org: '', Receiver_account: addresses[2], Receiver_org: '',
      MultiReceiver_account: ethers.ZeroAddress, MultiReceiver_org: 'receiver-org'
    };
    await tx(contract.createInstance(params, { gasLimit: 2000000 }));
    await tx(contract.createInstance(params, { gasLimit: 2000000 }));
    const messageStates = async (id = 0) => Array.from((await contract.getExecutionSnapshot(id)).messageStates, Number);
    await reverted('Complete before Send rejected', () => contract.connect(receiver).M_Complete.staticCall(0), 'message not waiting');
    await reverted('Unauthorized sender rejected', () => contract.connect(outsider).M_Send.staticCall(0, 'tx', 42), 'participant not allowed');
    await tx(contract.connect(sender).M_Send(0, 'firefly-42', 42));
    let states = await messageStates();
    assert.equal(states[0], 2); assert.equal(states[2], 1); assert.equal(states[3], 0);
    assert.equal((await messageStates(1))[0], 1);
    assert.equal((await contract.getExecutionSnapshot(0)).messageFireflyTranIds[0], 'firefly-42');
    checks.push('Send enters WAITING; sent actions only; transaction ID retained; instances isolated');
    await tx(contract.Data(0));
    states = await messageStates(); assert.equal(states[4], 1); assert.equal(states[5], 0);
    checks.push('Send writes payload to global memory (verified through value-dependent gateway)');
    await reverted('Repeated Send while waiting rejected', () => contract.connect(sender).M_Send.staticCall(0, 'retry', 7), 'message state not allowed');
    await reverted('Sender cannot confirm for receiver', () => contract.connect(sender).M_Complete.staticCall(0), 'participant not allowed');
    await reverted('Third party cannot confirm', () => contract.connect(outsider).M_Complete.staticCall(0), 'participant not allowed');
    await reverted('Parallel join rejects pending inputs', () => contract.Join.staticCall(0), 'Parallel gateway prerequisites not met');
    const receipt = await tx(contract.connect(receiver).M_Complete(0));
    const completed = receipt.logs.map(log => { try { return contract.interface.parseLog(log); } catch { return null; } }).find(log => log?.name === 'MessageCompleted');
    assert(completed); assert.equal(completed.args.instanceId, 0n); assert.equal(completed.args.fireflyTranId, 'firefly-42');
    states = await messageStates(); assert.equal(states[0], 3); assert.equal(states[3], 1);
    checks.push('Receiver confirmation completes message, emits retained ID and runs completed actions');
    await reverted('Duplicate Complete rejected', () => contract.connect(receiver).M_Complete.staticCall(0), 'message not waiting');
    await reverted('Send after completion rejected', () => contract.connect(sender).M_Send.staticCall(0, 'again', 7), 'message state not allowed');
    await tx(contract.connect(sender).M2_Send(0, 'second'));
    await reverted('Parallel join rejects remaining waiting message', () => contract.Join.staticCall(0), 'Parallel gateway prerequisites not met');
    await tx(contract.connect(receiver).M2_Complete(0));
    await tx(contract.Join(0));
    assert.equal(Number((await contract.getExecutionSnapshot(0)).eventStates[0]), 1);
    checks.push('Parallel join proceeds only once both source messages are completed');
    await tx(contract.connect(sender).Multi_Send(0, 'multi'));
    await reverted('Wrong organization cannot confirm multi participant', () => contract.connect(outsider).Multi_Complete.staticCall(0), 'participant org not allowed');
    await tx(contract.connect(multiReceiver).Multi_Complete(0));
    assert.equal((await messageStates())[6], 3);
    checks.push('Multi participant receiver confirms using existing organization identity guard');
    await reverted('Missing instance rejected', () => contract.connect(receiver).M_Complete.staticCall(99), 'instance not found');
    fs.writeFileSync(reportPath, JSON.stringify({ status: 'PASS', environment: 'in-process Ganache local EVM; no external network deployment', solc: solc.version(), checks }, null, 2) + '\n');
    console.log(JSON.stringify({ status: 'PASS', checks: checks.length, reportPath }));
  } finally { await chain.disconnect(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
