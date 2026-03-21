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

const MALICIOUS_RATIOS = [0, 0.2, 0.4];
const ERROR_TOLERANCE = 50; // with scale=100 => 0.50

function abs(x) {
  return x < 0 ? -x : x;
}

function maliciousCount(total, ratio) {
  return Math.max(0, Math.min(total, Math.floor(total * ratio + 1e-9)));
}

function buildObservations(round, ratio, totalNodes) {
  const obs = [...round.clean];
  const m = maliciousCount(totalNodes, ratio);
  for (let i = 0; i < m; i++) {
    if (i % 2 === 0) {
      obs[i] = Math.round(round.truth * (1.20 + 0.05 * i));
    } else {
      obs[i] = Math.round(round.truth * (0.80 - 0.03 * i));
    }
  }
  return { obs, malicious: m };
}

async function signData(oracleSigner, contractAddress, taskId, value) {
  const digest = hre.ethers.solidityPackedKeccak256(
    ["address", "bytes32", "uint256", "uint256"],
    [contractAddress, DATA_DOMAIN, taskId, value]
  );
  return oracleSigner.signMessage(hre.ethers.getBytes(digest));
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

  const OracleFactory = await hre.ethers.getContractFactory("UnifiedOracleLab");
  const oracle = await OracleFactory.connect(owner).deploy();
  await oracle.waitForDeployment();

  for (const addr of oracleAddresses) {
    await (await oracle.connect(owner).registerOracle(addr)).wait();
  }

  const report = {
    generatedAt: new Date().toISOString(),
    title: "Data Aggregation Benchmark under Byzantine Ratios",
    symbol: dataset.symbol,
    rounds: dataset.rounds.length,
    maliciousRatios: MALICIOUS_RATIOS,
    errorTolerance: ERROR_TOLERANCE,
    methods: {},
    references: [
      {
        key: "Yin2018",
        title: "Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates",
        url: "https://arxiv.org/abs/1803.01498"
      },
      {
        key: "Blanchard2017",
        title: "Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent",
        url: "https://papers.nips.cc/paper_files/paper/2017/hash/f4b9ec30ad9f68f89b29639786cb62ef-Abstract.html"
      },
      {
        key: "ChainlinkFeeds",
        title: "Chainlink Data Feeds architecture",
        url: "https://chain.link/data-feeds"
      }
    ]
  };

  for (const [modeName, mode] of Object.entries(MODES)) {
    report.methods[modeName] = {};
    for (const ratio of MALICIOUS_RATIOS) {
      const errors = [];
      let totalGas = 0n;
      let okCount = 0;
      let attackNodes = 0;

      for (const round of dataset.rounds) {
        const { obs, malicious } = buildObservations(round, ratio, oracleSigners.length);
        attackNodes += malicious;

        const sourceConfig = JSON.stringify({
          symbol: dataset.symbol,
          ts: round.ts,
          ratio
        });
        const regTx = await oracle
          .connect(owner)
          .registerDataTask(sourceConfig, mode, oracleAddresses, weights, oracleAddresses.length);
        const regRc = await regTx.wait();
        totalGas += regRc.gasUsed;
        const taskId = Number((await oracle.totalDataTasks()).toString());

        for (let i = 0; i < oracleSigners.length; i++) {
          const sig = await signData(oracleSigners[i], oracle.target, taskId, obs[i]);
          const tx = await oracle.connect(oracleSigners[i]).submitData(taskId, obs[i], sig);
          const rc = await tx.wait();
          totalGas += rc.gasUsed;
        }

        const resultTuple = await oracle.getDataTaskResult(taskId);
        const finalValue = Number(resultTuple[1].toString());
        const err = abs(finalValue - round.truth);
        errors.push(err);
        if (err <= ERROR_TOLERANCE) {
          okCount += 1;
        }
      }

      report.methods[modeName][`ratio_${ratio}`] = {
        maliciousNodesAvgPerRound: attackNodes / dataset.rounds.length,
        mae: mean(errors),
        rmse: Math.sqrt(mean(errors.map((x) => x * x))),
        stddev: stddev(errors),
        successRate: okCount / dataset.rounds.length,
        avgTotalGas: Number(totalGas) / dataset.rounds.length
      };
    }
  }

  const outPath = path.join(root, "report", "experiment-data-benchmark.json");
  writeJson(outPath, report);
  console.log(`data benchmark report -> ${outPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
