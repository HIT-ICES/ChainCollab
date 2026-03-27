const path = require("path");
const fs = require("fs");
const hre = require("hardhat");
const { ethers } = require("ethers");
const {
  loadDevnetConfig,
  ensureDir,
  writeJson,
  DEPLOYMENTS_DIR,
  deriveWallet
} = require("./common");

async function main() {
  const splitSpecPath = path.join(DEPLOYMENTS_DIR, "bpmn-split-cases.json");
  if (!fs.existsSync(splitSpecPath)) {
    throw new Error(`missing ${splitSpecPath}. run npm run prepare:bpmn:split first`);
  }
  const splitSpec = JSON.parse(fs.readFileSync(splitSpecPath, "utf8"));
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
  const relayerAddress = await relayerOnTarget.getAddress();

  const deployedCases = [];
  for (const c of splitSpec.cases) {
    const sourceName = c.generatedArtifacts.splitContracts.sourceContractName;
    const targetName = c.generatedArtifacts.splitContracts.targetContractName;
    const subA = c.split.submodels[0] || { entryNodes: ["UNKNOWN"], exitNodes: ["UNKNOWN"] };
    const subB = c.split.submodels[1] || { entryNodes: ["UNKNOWN"], exitNodes: ["UNKNOWN"] };

    const SourceFactory = await hre.ethers.getContractFactory(sourceName, deployerOnSource);
    const sourceCtorInputs = SourceFactory.interface.deploy.inputs || [];
    const sourceArgs = [];
    if (sourceCtorInputs.length >= 1) {
      sourceArgs.push(String((subA.entryNodes && subA.entryNodes[0]) || "UNKNOWN"));
    }
    if (sourceCtorInputs.length >= 2) {
      sourceArgs.push(String((subA.exitNodes && subA.exitNodes[0]) || "UNKNOWN"));
    }
    const source = await SourceFactory.deploy(...sourceArgs);
    await source.waitForDeployment();

    const TargetFactory = await hre.ethers.getContractFactory(targetName, deployerOnTarget);
    const targetCtorInputs = TargetFactory.interface.deploy.inputs || [];
    const targetArgs = [];
    if (targetCtorInputs.length >= 1) {
      targetArgs.push(String((subB.entryNodes && subB.entryNodes[0]) || "UNKNOWN"));
    }
    if (targetCtorInputs.length >= 2) {
      targetArgs.push(String((subB.exitNodes && subB.exitNodes[0]) || "UNKNOWN"));
    }
    const target = await TargetFactory.deploy(...targetArgs);
    await target.waitForDeployment();

    const allowTx = await target.connect(deployerOnTarget).setRelayer(relayerAddress, true);
    await allowTx.wait();

    const sourceDeployTx = await source.deploymentTransaction();
    const targetDeployTx = await target.deploymentTransaction();
    const sourceDeployRc = sourceDeployTx ? await sourceDeployTx.wait() : null;
    const targetDeployRc = targetDeployTx ? await targetDeployTx.wait() : null;

    deployedCases.push({
      caseId: c.caseId,
      source: {
        chainId: cfg.source.chainId,
        rpcUrl: cfg.source.rpcUrl,
        contractName: sourceName,
        contractAddress: source.target,
        deployBlock: sourceDeployRc?.blockNumber || null
      },
      target: {
        chainId: cfg.target.chainId,
        rpcUrl: cfg.target.rpcUrl,
        contractName: targetName,
        contractAddress: target.target,
        deployBlock: targetDeployRc?.blockNumber || null
      }
    });
  }

  const deployed = {
    generatedAt: new Date().toISOString(),
    sourceChain: {
      chainId: cfg.source.chainId,
      rpcUrl: cfg.source.rpcUrl
    },
    targetChain: {
      chainId: cfg.target.chainId,
      rpcUrl: cfg.target.rpcUrl
    },
    accounts: {
      deployer: await deployerOnSource.getAddress(),
      relayer: relayerAddress
    },
    derivation: {
      mnemonic: cfg.mnemonic,
      deployerIndex: cfg.deployerIndex,
      relayerIndex: cfg.relayerIndex
    },
    cases: deployedCases
  };

  const outPath = path.join(DEPLOYMENTS_DIR, "split-generated-addresses.json");
  ensureDir(path.dirname(outPath));
  writeJson(outPath, deployed);
  console.log(`split generated deployment file: ${outPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
