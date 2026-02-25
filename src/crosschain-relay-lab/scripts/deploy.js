const { ethers } = require("ethers");
const {
  DEFAULTS,
  LOCAL_DEPLOY_FILE,
  readArtifact,
  writeJson
} = require("./common");

async function deployOne(signer, artifact, args = []) {
  const factory = new ethers.ContractFactory(
    artifact.abi,
    artifact.bytecode,
    signer
  );
  const c = await factory.deploy(...args);
  await c.waitForDeployment();
  return c;
}

async function waitForRpc(provider, label, timeoutMs = 12000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      await provider.getBlockNumber();
      return;
    } catch (err) {
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
  }
  throw new Error(`rpc not ready: ${label}`);
}

async function main() {
  const endpointArtifact = readArtifact("CrossChainEndpoint");
  const receiverArtifact = readArtifact("RelayTaskReceiver");
  const iiotArtifact = readArtifact("IndustrialIoTReceiver");

  const providerA = new ethers.JsonRpcProvider(DEFAULTS.chainA.rpcUrl);
  const providerB = new ethers.JsonRpcProvider(DEFAULTS.chainB.rpcUrl);
  await waitForRpc(providerA, DEFAULTS.chainA.rpcUrl);
  await waitForRpc(providerB, DEFAULTS.chainB.rpcUrl);

  const deployerA = new ethers.NonceManager(
    new ethers.Wallet(DEFAULTS.keys.deployer, providerA)
  );
  const deployerB = new ethers.NonceManager(
    new ethers.Wallet(DEFAULTS.keys.deployer, providerB)
  );
  const relayerA = new ethers.NonceManager(
    new ethers.Wallet(DEFAULTS.keys.relayer, providerA)
  );
  const relayerB = new ethers.NonceManager(
    new ethers.Wallet(DEFAULTS.keys.relayer, providerB)
  );

  const [chainIdA, chainIdB] = await Promise.all([
    providerA.getNetwork().then((n) => Number(n.chainId)),
    providerB.getNetwork().then((n) => Number(n.chainId))
  ]);
  const relayerAddressA = await relayerA.getAddress();
  const relayerAddressB = await relayerB.getAddress();

  console.log(`deploy chainA id=${chainIdA} rpc=${DEFAULTS.chainA.rpcUrl}`);
  const endpointA = await deployOne(deployerA, endpointArtifact);
  const receiverA = await deployOne(deployerA, receiverArtifact);
  const iiotA = await deployOne(deployerA, iiotArtifact);

  console.log(`deploy chainB id=${chainIdB} rpc=${DEFAULTS.chainB.rpcUrl}`);
  const endpointB = await deployOne(deployerB, endpointArtifact);
  const receiverB = await deployOne(deployerB, receiverArtifact);
  const iiotB = await deployOne(deployerB, iiotArtifact);

  await (await endpointA.connect(deployerA).setRelayer(relayerAddressA, true)).wait();
  await (await endpointB.connect(deployerB).setRelayer(relayerAddressB, true)).wait();
  await (await endpointA.connect(deployerA).setAllowedTarget(await receiverA.getAddress(), true)).wait();
  await (await endpointB.connect(deployerB).setAllowedTarget(await receiverB.getAddress(), true)).wait();
  await (await endpointA.connect(deployerA).setAllowedTarget(await iiotA.getAddress(), true)).wait();
  await (await endpointB.connect(deployerB).setAllowedTarget(await iiotB.getAddress(), true)).wait();

  const payload = {
    generatedAt: new Date().toISOString(),
    chainA: {
      name: DEFAULTS.chainA.name,
      chainId: chainIdA,
      rpcUrl: DEFAULTS.chainA.rpcUrl,
      endpoint: await endpointA.getAddress(),
      receiver: await receiverA.getAddress(),
      iiotReceiver: await iiotA.getAddress()
    },
    chainB: {
      name: DEFAULTS.chainB.name,
      chainId: chainIdB,
      rpcUrl: DEFAULTS.chainB.rpcUrl,
      endpoint: await endpointB.getAddress(),
      receiver: await receiverB.getAddress(),
      iiotReceiver: await iiotB.getAddress()
    },
    accounts: {
      deployer: await deployerA.getAddress(),
      relayer: relayerAddressA,
      user: new ethers.Wallet(DEFAULTS.keys.user).address
    }
  };

  writeJson(LOCAL_DEPLOY_FILE, payload);
  console.log(`deployment saved: ${LOCAL_DEPLOY_FILE}`);
  console.log(payload);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
