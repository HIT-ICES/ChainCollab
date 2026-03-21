const fs = require("fs");
const path = require("path");
const hre = require("hardhat");
const { mean, writeJson } = require("./common");
const DATA_DOMAIN = hre.ethers.id("DATA");
const COMPUTE_DOMAIN = hre.ethers.id("COMPUTE");

const DATA_MODES = {
  MEAN: 0,
  MEDIAN: 1,
  WEIGHTED_MEAN: 2,
  TRIMMED_MEAN: 3
};

const COMPUTE_STRATEGIES = {
  FIRST_RESPONSE: 1,
  MAJORITY: 3,
  STRICT_ALL: 5
};

const MALICIOUS_RATIOS = [0, 0.2, 0.4];
const DATA_TOLERANCE = 50;

function abs(x) {
  return x < 0 ? -x : x;
}

function mCount(total, ratio) {
  return Math.max(0, Math.min(total, Math.floor(total * ratio + 1e-9)));
}

function buildDataObs(round, ratio, totalNodes) {
  const obs = [...round.clean];
  const m = mCount(totalNodes, ratio);
  for (let i = 0; i < m; i++) {
    obs[i] = Math.round(round.truth * (1.30 + 0.05 * i));
  }
  return { obs, malicious: m };
}

function computeValue(x0, x1) {
  return Math.floor(((x0 * 2) + x1) / 10);
}

function computeWrongValue(x0, x1) {
  return Math.floor(((x0 * 2) + x1) / 7);
}

function resultHash(result) {
  const coder = hre.ethers.AbiCoder.defaultAbiCoder();
  const encoded = coder.encode(["uint256"], [BigInt(result)]);
  return hre.ethers.keccak256(encoded);
}

function encodeComputeType(str) {
  const b = Buffer.from(str, "utf8");
  if (b.length > 32) return hre.ethers.keccak256(hre.ethers.toUtf8Bytes(str));
  return hre.ethers.zeroPadValue(hre.ethers.hexlify(b), 32);
}

async function signData(oracleSigner, contractAddress, taskId, value) {
  const digest = hre.ethers.solidityPackedKeccak256(
    ["address", "bytes32", "uint256", "uint256"],
    [contractAddress, DATA_DOMAIN, taskId, value]
  );
  return oracleSigner.signMessage(hre.ethers.getBytes(digest));
}

async function signCompute(oracleSigner, contractAddress, taskId, hashed) {
  const digest = hre.ethers.solidityPackedKeccak256(
    ["address", "bytes32", "uint256", "bytes32"],
    [contractAddress, COMPUTE_DOMAIN, taskId, hashed]
  );
  return oracleSigner.signMessage(hre.ethers.getBytes(digest));
}

async function runDataSide(oracle, owner, oracleSigners, oracleAddresses, rounds, ratio, mode, weights) {
  let pass = 0;
  for (const round of rounds) {
    const { obs } = buildDataObs(round, ratio, oracleSigners.length);
    const sourceConfig = JSON.stringify({ ts: round.ts, ratio, side: "data" });
    await (
      await oracle
        .connect(owner)
        .registerDataTask(sourceConfig, mode, oracleAddresses, weights, oracleAddresses.length)
    ).wait();
    const taskId = Number((await oracle.totalDataTasks()).toString());

    for (let i = 0; i < oracleSigners.length; i++) {
      const sig = await signData(oracleSigners[i], oracle.target, taskId, obs[i]);
      await (await oracle.connect(oracleSigners[i]).submitData(taskId, obs[i], sig)).wait();
    }

    const tuple = await oracle.getDataTaskResult(taskId);
    const v = Number(tuple[1].toString());
    if (abs(v - round.truth) <= DATA_TOLERANCE) {
      pass += 1;
    }
  }
  return pass / rounds.length;
}

async function runComputeSide(
  oracle,
  owner,
  oracleSigners,
  oracleAddresses,
  payloads,
  ratio,
  threshold
) {
  const malicious = mCount(oracleSigners.length, ratio);
  let finalized = 0;
  let correct = 0;

  for (const row of payloads) {
    const payloadJson = JSON.stringify({ task_id: row.task_id, x0: row.x0, x1: row.x1 });
    const pHash = hre.ethers.keccak256(hre.ethers.toUtf8Bytes(payloadJson));
    await (
      await oracle
        .connect(owner)
        .registerComputeTask(
          encodeComputeType(row.compute_type),
          pHash,
          oracleAddresses,
          threshold
        )
    ).wait();
    const taskId = Number((await oracle.totalComputeTasks()).toString());

    const goodHash = resultHash(computeValue(row.x0, row.x1));
    const badHash = resultHash(computeWrongValue(row.x0, row.x1));

    const order = [];
    for (let i = 0; i < malicious; i++) order.push(i);
    for (let i = malicious; i < oracleSigners.length; i++) order.push(i);

    for (const idx of order) {
      const signer = oracleSigners[idx];
      const isBad = idx < malicious;
      const h = isBad ? badHash : goodHash;
      const sig = await signCompute(signer, oracle.target, taskId, h);
      try {
        await (await oracle.connect(signer).submitComputeResult(taskId, h, sig)).wait();
      } catch (_e) {
        // ignore if task is already finalized
      }
      const tupleMid = await oracle.getComputeTaskResult(taskId);
      if (tupleMid[0]) break;
    }

    const tuple = await oracle.getComputeTaskResult(taskId);
    const done = Boolean(tuple[0]);
    if (done) {
      finalized += 1;
      if (String(tuple[1]).toLowerCase() === goodHash.toLowerCase()) {
        correct += 1;
      }
    }
  }

  return {
    finalizeRate: finalized / payloads.length,
    correctnessRate: correct / payloads.length
  };
}

async function main() {
  const root = path.join(__dirname, "..");
  const stock = JSON.parse(
    fs.readFileSync(path.join(root, "dataset", "stock_price_scenarios.json"), "utf8")
  );
  const computeDataset = JSON.parse(
    fs.readFileSync(path.join(root, "dataset", "compute_payloads.json"), "utf8")
  );

  const [owner, ...signers] = await hre.ethers.getSigners();
  const oracleSigners = signers.slice(0, 5);
  const oracleAddresses = await Promise.all(oracleSigners.map((s) => s.getAddress()));
  const weights = [40, 25, 15, 10, 10];

  const report = {
    generatedAt: new Date().toISOString(),
    maliciousRatios: MALICIOUS_RATIOS,
    dataTolerance: DATA_TOLERANCE,
    dataSide: {},
    computeSide: {},
    combined: {}
  };

  for (const ratio of MALICIOUS_RATIOS) {
    const ratioKey = `ratio_${ratio}`;
    report.dataSide[ratioKey] = {};
    report.computeSide[ratioKey] = {};

    for (const [modeName, mode] of Object.entries(DATA_MODES)) {
      const OF = await hre.ethers.getContractFactory("UnifiedOracleLab");
      const oracle = await OF.connect(owner).deploy();
      await oracle.waitForDeployment();
      for (const addr of oracleAddresses) {
        await (await oracle.connect(owner).registerOracle(addr)).wait();
      }
      const succ = await runDataSide(
        oracle,
        owner,
        oracleSigners,
        oracleAddresses,
        stock.rounds,
        ratio,
        mode,
        weights
      );
      report.dataSide[ratioKey][modeName] = { successRate: succ };
    }

    for (const [strategy, threshold] of Object.entries(COMPUTE_STRATEGIES)) {
      const OF = await hre.ethers.getContractFactory("UnifiedOracleLab");
      const oracle = await OF.connect(owner).deploy();
      await oracle.waitForDeployment();
      for (const addr of oracleAddresses) {
        await (await oracle.connect(owner).registerOracle(addr)).wait();
      }
      const computeRes = await runComputeSide(
        oracle,
        owner,
        oracleSigners,
        oracleAddresses,
        computeDataset.rounds,
        ratio,
        threshold
      );
      report.computeSide[ratioKey][strategy] = computeRes;
    }

    const dataAvg = mean(
      Object.values(report.dataSide[ratioKey]).map((item) => item.successRate)
    );
    const computeAvg = mean(
      Object.values(report.computeSide[ratioKey]).map((item) => item.correctnessRate)
    );
    report.combined[ratioKey] = {
      dataAvgSuccess: dataAvg,
      computeAvgCorrectness: computeAvg,
      overallScore: (dataAvg + computeAvg) / 2
    };
  }

  const outPath = path.join(root, "report", "experiment-overall-bft.json");
  writeJson(outPath, report);
  console.log(`overall bft report -> ${outPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
