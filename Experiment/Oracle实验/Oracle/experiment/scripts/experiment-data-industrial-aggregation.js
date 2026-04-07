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

async function signData(oracleSigner, contractAddress, taskId, value) {
  const digest = hre.ethers.solidityPackedKeccak256(
    ["address", "bytes32", "uint256", "uint256"],
    [contractAddress, DATA_DOMAIN, taskId, value]
  );
  return oracleSigner.signMessage(hre.ethers.getBytes(digest));
}

function modeRank(metricsObj) {
  return Object.entries(metricsObj)
    .map(([mode, m]) => ({ mode, mae: m.mae, rmse: m.rmse, avgTotalGas: m.avgTotalGas }))
    .sort((a, b) => {
      if (a.mae !== b.mae) return a.mae - b.mae;
      if (a.rmse !== b.rmse) return a.rmse - b.rmse;
      return a.avgTotalGas - b.avgTotalGas;
    });
}

async function main() {
  const root = path.join(__dirname, "..");
  const datasetPath = path.join(root, "dataset", "industrial_data_aggregation_scenarios.json");
  const dataset = JSON.parse(fs.readFileSync(datasetPath, "utf8"));

  const [owner, ...signers] = await hre.ethers.getSigners();
  const nodeCount = Number(dataset.oracle_node_count || 5);
  if (signers.length < nodeCount) {
    throw new Error(`not enough local signers: need=${nodeCount} got=${signers.length}`);
  }
  const oracleSigners = signers.slice(0, nodeCount);
  const oracleAddresses = await Promise.all(oracleSigners.map((s) => s.getAddress()));
  const defaultWeights = Array.from({ length: nodeCount }, () => 1);

  const OracleFactory = await hre.ethers.getContractFactory("UnifiedOracleLab");
  const oracle = await OracleFactory.connect(owner).deploy();
  await oracle.waitForDeployment();
  for (const addr of oracleAddresses) {
    await (await oracle.connect(owner).registerOracle(addr)).wait();
  }

  const report = {
    generatedAt: new Date().toISOString(),
    datasetFile: path.basename(datasetPath),
    profileNames: dataset.profiles.map((x) => x.name),
    profileMeta: dataset.profiles,
    modes: Object.keys(MODES),
    scenarios: [],
    summary: {
      overallByMode: {}
    }
  };

  const modeBucket = {};
  for (const modeName of Object.keys(MODES)) {
    modeBucket[modeName] = {
      mae: [],
      rmse: [],
      mape: [],
      avgTotalGas: []
    };
  }

  for (const scenario of dataset.scenarios) {
    const scenarioResult = {
      uciId: scenario.uci_id,
      datasetName: scenario.dataset_name,
      datasetRef: scenario.dataset_ref,
      metricCol: scenario.metric_col,
      roundCount: scenario.round_count,
      profiles: {},
      rankingByProfile: {}
    };

    for (const profileMeta of dataset.profiles) {
      const profileName = profileMeta.name;
      const profileWeights =
        Array.isArray(dataset.profile_weights?.[profileName]) &&
        dataset.profile_weights[profileName].length === nodeCount
          ? dataset.profile_weights[profileName].map((x) => Number(x))
          : defaultWeights;
      scenarioResult.profiles[profileName] = {};

      for (const [modeName, mode] of Object.entries(MODES)) {
        const errors = [];
        const apeList = [];
        let totalGas = 0n;
        let totalRegisterGas = 0n;
        let totalSubmitGas = 0n;
        let validRounds = 0;

        for (const round of scenario.rounds) {
          const obs = round.profiles[profileName];
          if (!obs || !Array.isArray(obs) || obs.length !== nodeCount) {
            throw new Error(
              `profile size mismatch: scenario=${scenario.dataset_name} profile=${profileName} round=${round.idx}`
            );
          }
          const validIdx = [];
          for (let i = 0; i < obs.length; i++) {
            if (obs[i] !== null && obs[i] !== undefined) {
              validIdx.push(i);
            }
          }
          if (validIdx.length < 3) {
            continue;
          }

          const minResponses = validIdx.length;
          const sourceConfig = JSON.stringify({
            scenario: scenario.dataset_name,
            metric: scenario.metric_col,
            profile: profileName,
            roundIdx: round.idx
          });

          const regTx = await oracle
            .connect(owner)
            .registerDataTask(sourceConfig, mode, oracleAddresses, profileWeights, minResponses);
          const regRc = await regTx.wait();
          totalGas += regRc.gasUsed;
          totalRegisterGas += regRc.gasUsed;
          const taskId = Number((await oracle.totalDataTasks()).toString());

          for (const i of validIdx) {
            const v = obs[i];
            const sig = await signData(oracleSigners[i], oracle.target, taskId, v);
            const tx = await oracle.connect(oracleSigners[i]).submitData(taskId, v, sig);
            const rc = await tx.wait();
            totalGas += rc.gasUsed;
            totalSubmitGas += rc.gasUsed;
          }

          const resultTuple = await oracle.getDataTaskResult(taskId);
          const finalValue = Number(resultTuple[1].toString());
          const err = abs(finalValue - round.truth);
          errors.push(err);
          if (round.truth > 0) {
            apeList.push(err / round.truth);
          }
          validRounds += 1;
        }

        scenarioResult.profiles[profileName][modeName] = {
          validRounds,
          mae: mean(errors),
          rmse: Math.sqrt(mean(errors.map((x) => x * x))),
          mape: mean(apeList),
          stddev: stddev(errors),
          avgTotalGas: validRounds > 0 ? Number(totalGas) / validRounds : 0,
          avgRegisterGas: validRounds > 0 ? Number(totalRegisterGas) / validRounds : 0,
          avgSubmitGas: validRounds > 0 ? Number(totalSubmitGas) / validRounds : 0
        };

        modeBucket[modeName].mae.push(scenarioResult.profiles[profileName][modeName].mae);
        modeBucket[modeName].rmse.push(scenarioResult.profiles[profileName][modeName].rmse);
        modeBucket[modeName].mape.push(scenarioResult.profiles[profileName][modeName].mape);
        modeBucket[modeName].avgTotalGas.push(
          scenarioResult.profiles[profileName][modeName].avgTotalGas
        );
      }

      scenarioResult.rankingByProfile[profileName] = modeRank(
        scenarioResult.profiles[profileName]
      );
    }

    report.scenarios.push(scenarioResult);
  }

  for (const modeName of Object.keys(MODES)) {
    report.summary.overallByMode[modeName] = {
      meanMAE: mean(modeBucket[modeName].mae),
      meanRMSE: mean(modeBucket[modeName].rmse),
      meanMAPE: mean(modeBucket[modeName].mape),
      meanAvgTotalGas: mean(modeBucket[modeName].avgTotalGas)
    };
  }

  report.summary.overallRanking = modeRank(
    Object.fromEntries(
      Object.entries(report.summary.overallByMode).map(([k, v]) => [
        k,
        {
          mae: v.meanMAE,
          rmse: v.meanRMSE,
          avgTotalGas: v.meanAvgTotalGas
        }
      ])
    )
  );

  const outPath = path.join(root, "report", "data-industrial-aggregation-report.json");
  writeJson(outPath, report);
  console.log(`industrial data aggregation report -> ${outPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
