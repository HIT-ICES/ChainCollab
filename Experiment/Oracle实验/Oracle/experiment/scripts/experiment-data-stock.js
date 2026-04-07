const fs = require("fs");
const path = require("path");
const hre = require("hardhat");
const { mean, stddev, writeJson } = require("./common");
const DATA_DOMAIN = hre.ethers.id("DATA");

const MODES = {
  MEAN: 0,
  MEDIAN: 1,
  WEIGHTED_MEAN: 2,
  TRIMMED_MEAN: 3
};

function abs(x) {
  return x < 0 ? -x : x;
}

async function signData(oracle, contractAddress, taskId, value) {
  const digest = hre.ethers.solidityPackedKeccak256(
    ["address", "bytes32", "uint256", "uint256"],
    [contractAddress, DATA_DOMAIN, taskId, value]
  );
  return oracle.signMessage(hre.ethers.getBytes(digest));
}

async function main() {
  const root = path.join(__dirname, "..");
  const dataset = JSON.parse(
    fs.readFileSync(path.join(root, "dataset", "stock_price_scenarios.json"), "utf8")
  );

  const [owner, ...signers] = await hre.ethers.getSigners();
  const oracleSigners = signers.slice(0, 5);
  const oracleAddresses = await Promise.all(oracleSigners.map((s) => s.getAddress()));
  const weights = [40, 25, 15, 10, 10];

  const Factory = await hre.ethers.getContractFactory("UnifiedOracleLab");
  const oracle = await Factory.connect(owner).deploy();
  await oracle.waitForDeployment();

  for (const addr of oracleAddresses) {
    const tx = await oracle.connect(owner).registerOracle(addr);
    await tx.wait();
  }

  const report = {
    generatedAt: new Date().toISOString(),
    symbol: dataset.symbol,
    rounds: dataset.rounds.length,
    scenarios: {},
    settings: {
      priceScale: dataset.price_scale,
      minResponses: oracleAddresses.length
    }
  };

  for (const scenarioName of ["clean", "malicious"]) {
    report.scenarios[scenarioName] = {};

    for (const modeName of Object.keys(MODES)) {
      const mode = MODES[modeName];
      const errors = [];
      let totalGas = 0n;
      let registerGas = 0n;
      let submitGas = 0n;

      for (const round of dataset.rounds) {
        const sourceConfig = JSON.stringify({
          symbol: dataset.symbol,
          ts: round.ts,
          scenario: scenarioName
        });

        const registerTx = await oracle
          .connect(owner)
          .registerDataTask(sourceConfig, mode, oracleAddresses, weights, oracleAddresses.length);
        const registerRc = await registerTx.wait();
        const taskId = Number((await oracle.totalDataTasks()).toString());

        registerGas += registerRc.gasUsed;
        totalGas += registerRc.gasUsed;

        const obs = round[scenarioName];
        for (let i = 0; i < oracleSigners.length; i++) {
          const sig = await signData(oracleSigners[i], oracle.target, taskId, obs[i]);
          const submitTx = await oracle.connect(oracleSigners[i]).submitData(taskId, obs[i], sig);
          const submitRc = await submitTx.wait();
          submitGas += submitRc.gasUsed;
          totalGas += submitRc.gasUsed;
        }

        const resultTuple = await oracle.getDataTaskResult(taskId);
        const finalValue = Number(resultTuple[1].toString());
        errors.push(abs(finalValue - round.truth));
      }

      report.scenarios[scenarioName][modeName] = {
        mae: mean(errors),
        stddev: stddev(errors),
        avgTotalGas: Number(totalGas) / dataset.rounds.length,
        avgRegisterGas: Number(registerGas) / dataset.rounds.length,
        avgSubmitGas: Number(submitGas) / dataset.rounds.length
      };
    }
  }

  report.robustness = {};
  for (const modeName of Object.keys(MODES)) {
    const cleanMae = report.scenarios.clean[modeName].mae;
    const attackMae = report.scenarios.malicious[modeName].mae;
    report.robustness[modeName] = {
      maeIncrease: attackMae - cleanMae,
      ratio: cleanMae === 0 ? null : attackMae / cleanMae
    };
  }

  const outPath = path.join(root, "report", "data-stock-report.json");
  writeJson(outPath, report);
  console.log(`data experiment report -> ${outPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
