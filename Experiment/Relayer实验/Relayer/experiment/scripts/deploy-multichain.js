const path = require("path");
const hre = require("hardhat");
const { ethers } = require("ethers");
const {
  ensureDir,
  writeJson,
  loadDevnetConfig,
  deploymentPath,
  relayerStatePath,
  deriveWallet
} = require("./common");

async function main() {
  const cfg = loadDevnetConfig();

  const providerSource = new ethers.JsonRpcProvider(cfg.source.rpcUrl);
  const providerTarget = new ethers.JsonRpcProvider(cfg.target.rpcUrl);

  const deployerOnSource = new ethers.NonceManager(
    deriveWallet(cfg.mnemonic, cfg.deployerIndex, providerSource)
  );
  const deployerOnTarget = new ethers.NonceManager(
    deriveWallet(cfg.mnemonic, cfg.deployerIndex, providerTarget)
  );
  const relayerOnTarget = deriveWallet(cfg.mnemonic, cfg.relayerIndex, providerTarget);

  const SourceFactory = await hre.ethers.getContractFactory(
    "SourceTaskEmitter",
    deployerOnSource
  );
  const source = await SourceFactory.deploy();
  await source.waitForDeployment();

  const TargetFactory = await hre.ethers.getContractFactory(
    "TargetTaskReceiver",
    deployerOnTarget
  );
  const target = await TargetFactory.deploy();
  await target.waitForDeployment();

  const allowTx = await target
    .connect(deployerOnTarget)
    .setRelayer(await relayerOnTarget.getAddress(), true);
  await allowTx.wait();

  const sourceDeployTx = await source.deploymentTransaction();
  const targetDeployTx = await target.deploymentTransaction();
  const sourceDeployRc = sourceDeployTx ? await sourceDeployTx.wait() : null;
  const targetDeployRc = targetDeployTx ? await targetDeployTx.wait() : null;

  const deployed = {
    generatedAt: new Date().toISOString(),
    source: {
      chainId: cfg.source.chainId,
      rpcUrl: cfg.source.rpcUrl,
      contract: source.target,
      deployBlock: sourceDeployRc?.blockNumber || null
    },
    target: {
      chainId: cfg.target.chainId,
      rpcUrl: cfg.target.rpcUrl,
      contract: target.target,
      deployBlock: targetDeployRc?.blockNumber || null
    },
    accounts: {
      deployer: await deployerOnSource.getAddress(),
      relayer: await relayerOnTarget.getAddress()
    },
    derivation: {
      mnemonic: cfg.mnemonic,
      deployerIndex: cfg.deployerIndex,
      relayerIndex: cfg.relayerIndex
    }
  };

  const out = deploymentPath();
  ensureDir(path.dirname(out));
  writeJson(out, deployed);

  writeJson(relayerStatePath(), {
    generatedAt: new Date().toISOString(),
    sourceLastScannedBlock: (deployed.source.deployBlock || 0) - 1,
    relayedTasks: {}
  });

  console.log(`source contract: ${source.target}`);
  console.log(`target contract: ${target.target}`);
  console.log(`deployment file: ${out}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
