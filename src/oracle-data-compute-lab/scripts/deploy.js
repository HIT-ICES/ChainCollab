import hre from "hardhat";
import { readBuildArtifact, writeDeployment } from "./common.js";

const { ethers } = hre;

async function main() {
  const [owner, relayer, user] = await ethers.getSigners();
  const slotArtifact = readBuildArtifact("SlotRegistry");
  const dataArtifact = readBuildArtifact("DataOracleHub");
  const computeArtifact = readBuildArtifact("ComputeOracleHub");
  const aggregationArtifact = readBuildArtifact("DataAggregationLab");
  const computeCostArtifact = readBuildArtifact("ComputeCostLab");

  const slotFactory = new ethers.ContractFactory(
    slotArtifact.abi,
    slotArtifact.bytecode,
    owner
  );
  const slotRegistry = await slotFactory.deploy();
  await slotRegistry.waitForDeployment();
  const slotRegistryAddress = await slotRegistry.getAddress();

  const dataFactory = new ethers.ContractFactory(
    dataArtifact.abi,
    dataArtifact.bytecode,
    owner
  );
  const dataHub = await dataFactory.deploy(slotRegistryAddress);
  await dataHub.waitForDeployment();
  const dataHubAddress = await dataHub.getAddress();

  const computeFactory = new ethers.ContractFactory(
    computeArtifact.abi,
    computeArtifact.bytecode,
    owner
  );
  const computeHub = await computeFactory.deploy(slotRegistryAddress);
  await computeHub.waitForDeployment();
  const computeHubAddress = await computeHub.getAddress();

  const aggregationFactory = new ethers.ContractFactory(
    aggregationArtifact.abi,
    aggregationArtifact.bytecode,
    owner
  );
  const aggregationLab = await aggregationFactory.deploy(slotRegistryAddress);
  await aggregationLab.waitForDeployment();
  const aggregationLabAddress = await aggregationLab.getAddress();

  const computeCostFactory = new ethers.ContractFactory(
    computeCostArtifact.abi,
    computeCostArtifact.bytecode,
    owner
  );
  const computeCostLab = await computeCostFactory.deploy();
  await computeCostLab.waitForDeployment();
  const computeCostLabAddress = await computeCostLab.getAddress();

  await (await slotRegistry.connect(owner).setWriter(dataHubAddress, true)).wait();
  await (await slotRegistry.connect(owner).setWriter(computeHubAddress, true)).wait();
  await (await slotRegistry.connect(owner).setWriter(aggregationLabAddress, true)).wait();
  await (await dataHub.connect(owner).setRelayer(relayer.address, true)).wait();
  await (await computeHub.connect(owner).setRelayer(relayer.address, true)).wait();

  const payload = {
    chainId: (await ethers.provider.getNetwork()).chainId.toString(),
    contracts: {
      slotRegistry: {
        name: "SlotRegistry",
        address: slotRegistryAddress
      },
      dataOracleHub: {
        name: "DataOracleHub",
        address: dataHubAddress
      },
      computeOracleHub: {
        name: "ComputeOracleHub",
        address: computeHubAddress
      },
      dataAggregationLab: {
        name: "DataAggregationLab",
        address: aggregationLabAddress
      },
      computeCostLab: {
        name: "ComputeCostLab",
        address: computeCostLabAddress
      }
    },
    accounts: {
      owner: owner.address,
      relayer: relayer.address,
      user: user.address
    },
    generatedAt: new Date().toISOString()
  };

  writeDeployment(payload);
  console.log("SlotRegistry deployed:", slotRegistryAddress);
  console.log("DataOracleHub deployed:", dataHubAddress);
  console.log("ComputeOracleHub deployed:", computeHubAddress);
  console.log("DataAggregationLab deployed:", aggregationLabAddress);
  console.log("ComputeCostLab deployed:", computeCostLabAddress);
  console.log("deployment saved:", JSON.stringify(payload, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
