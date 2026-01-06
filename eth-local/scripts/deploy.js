import { ethers } from "hardhat";

async function main() {
  const Oracle = await ethers.getContractFactory("AggregatingOracle");
  const oracle = await Oracle.deploy();
  await oracle.waitForDeployment();
  console.log("AggregatingOracle deployed:", await oracle.getAddress());
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
