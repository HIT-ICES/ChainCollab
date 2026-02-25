const fs = require("fs");
const http = require("http");
const { URL } = require("url");
const Web3EthAbi = require("web3-eth-abi");

const RPC_URL = process.env.RPC_URL || "http://localhost:8545";
const DEPLOYMENT_DIR = "deployment";
const COMPILED_PATH = `${DEPLOYMENT_DIR}/compiled.json`;
const CHAINLINK_DEPLOYMENT_PATH = `${DEPLOYMENT_DIR}/chainlink-deployment.json`;
const OUTPUT_PATH = `${DEPLOYMENT_DIR}/oracle-task-suite.json`;
const EXPECTED_DEPLOYER = (
  process.env.DEPLOYER_ACCOUNT ||
  process.env.ETH_SYSTEM_ACCOUNT ||
  ""
).toLowerCase();

const MAIN_CONTRACT_KEY = "contracts/MainOracleRouter.sol:MainOracleRouter";
const DATA_ADAPTER_KEY =
  "contracts/ChainlinkDataTaskAdapter.sol:ChainlinkDataTaskAdapter";
const COMPUTE_ADAPTER_KEY =
  "contracts/ChainlinkComputeTaskAdapter.sol:ChainlinkComputeTaskAdapter";

function rpcCall(method, params) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      jsonrpc: "2.0",
      method,
      params,
      id: 1,
    });

    const rpc = new URL(RPC_URL);
    const options = {
      hostname: rpc.hostname,
      port: rpc.port || (rpc.protocol === "https:" ? 443 : 80),
      path: rpc.pathname === "" ? "/" : rpc.pathname,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(postData),
      },
    };

    const req = http.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => {
        data += chunk;
      });
      res.on("end", () => {
        const response = JSON.parse(data || "{}");
        if (response.error) {
          reject(new Error(response.error.message));
        } else {
          resolve(response.result);
        }
      });
    });

    req.on("error", reject);
    req.write(postData);
    req.end();
  });
}

function pickDeployer(accounts) {
  if (!Array.isArray(accounts) || accounts.length === 0) {
    throw new Error(`eth_accounts returned empty on ${RPC_URL}`);
  }
  if (EXPECTED_DEPLOYER) {
    const matched = accounts.find(
      (a) => String(a).toLowerCase() === EXPECTED_DEPLOYER
    );
    if (!matched) {
      throw new Error(
        `expected deployer ${EXPECTED_DEPLOYER} not found; got ${accounts.join(
          ", "
        )}`
      );
    }
    return matched;
  }
  return accounts[0];
}

function normalizeJobId(id) {
  if (!id) return "0x" + "0".repeat(64);
  let raw = String(id).toLowerCase().replace(/-/g, "");
  if (raw.startsWith("0x")) raw = raw.slice(2);
  if (!/^[0-9a-f]+$/.test(raw)) {
    throw new Error(`invalid job id: ${id}`);
  }
  if (raw.length > 64) {
    throw new Error(`job id too long: ${id}`);
  }
  return "0x" + raw.padEnd(64, "0");
}

async function waitForReceipt(txHash) {
  for (let i = 0; i < 60; i += 1) {
    const receipt = await rpcCall("eth_getTransactionReceipt", [txHash]);
    if (receipt) return receipt;
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error(`tx timeout: ${txHash}`);
}

async function sendTx(from, tx) {
  const txHash = await rpcCall("eth_sendTransaction", [{ from, ...tx }]);
  const receipt = await waitForReceipt(txHash);
  if (receipt.status === "0x0") {
    throw new Error(`tx failed: ${txHash}`);
  }
  return { txHash, receipt };
}

function encodeConstructor(contractData, args) {
  if (!args || args.length === 0) return "";
  const types = args.map((a) => a.type);
  const values = args.map((a) => a.value);
  return Web3EthAbi.encodeParameters(types, values).slice(2);
}

async function deployContract(from, compiled, contractKey, args = []) {
  const contractData = compiled.contracts[contractKey];
  if (!contractData) {
    throw new Error(`contract not found in compiled.json: ${contractKey}`);
  }
  const bytecode = "0x" + contractData.bin;
  const data = bytecode + encodeConstructor(contractData, args);

  const { txHash, receipt } = await sendTx(from, {
    data,
    gas: "0x" + (8000000).toString(16),
  });
  return {
    contractAddress: receipt.contractAddress,
    txHash,
  };
}

async function callMethod(from, to, abi, method, args = []) {
  const fn = abi.find((item) => item.type === "function" && item.name === method);
  if (!fn) throw new Error(`method ${method} not found in abi`);
  const data = Web3EthAbi.encodeFunctionCall(fn, args);
  const { txHash } = await sendTx(from, {
    to,
    data,
    gas: "0x" + (3000000).toString(16),
  });
  return txHash;
}

async function main() {
  if (!fs.existsSync(COMPILED_PATH)) {
    throw new Error(`missing ${COMPILED_PATH}, run ./compile.sh first`);
  }
  if (!fs.existsSync(CHAINLINK_DEPLOYMENT_PATH)) {
    throw new Error(
      `missing ${CHAINLINK_DEPLOYMENT_PATH}, run node scripts/deploy-chainlink.js first`
    );
  }

  const compiled = JSON.parse(fs.readFileSync(COMPILED_PATH, "utf8"));
  const chainlink = JSON.parse(
    fs.readFileSync(CHAINLINK_DEPLOYMENT_PATH, "utf8")
  );

  const accounts = await rpcCall("eth_accounts", []);
  const deployer = pickDeployer(accounts);

  const linkToken = chainlink.linkToken;
  const operator = chainlink.operator;
  const nodeAddress =
    process.env.CHAINLINK_NODE_ADDRESS || chainlink.chainlinkNodeAddress || "";

  if (!linkToken || !operator) {
    throw new Error("linkToken/operator missing in chainlink-deployment.json");
  }

  const dataJobId = normalizeJobId(
    process.env.DATA_TASK_JOB_ID ||
      chainlink.dataTaskJobId ||
      chainlink.dmnJobId ||
      chainlink.jobId
  );
  const computeJobId = normalizeJobId(
    process.env.COMPUTE_TASK_JOB_ID ||
      chainlink.computeTaskJobId ||
      chainlink.dmnJobId ||
      chainlink.jobId
  );
  const fee = process.env.ORACLE_TASK_FEE_WEI || "100000000000000000";

  console.log("RPC URL:", RPC_URL);
  console.log("deployer:", deployer);
  console.log("linkToken:", linkToken);
  console.log("operator:", operator);
  console.log("dataJobId:", dataJobId);
  console.log("computeJobId:", computeJobId);
  console.log("fee(wei):", fee);

  console.log("\n[1/5] deploy MainOracleRouter ...");
  const main = await deployContract(deployer, compiled, MAIN_CONTRACT_KEY, []);
  console.log("main:", main.contractAddress);

  console.log("\n[2/5] deploy ChainlinkDataTaskAdapter ...");
  const data = await deployContract(deployer, compiled, DATA_ADAPTER_KEY, [
    { type: "address", value: linkToken },
    { type: "address", value: operator },
    { type: "bytes32", value: dataJobId },
    { type: "uint256", value: fee },
    { type: "address", value: main.contractAddress },
  ]);
  console.log("data adapter:", data.contractAddress);

  console.log("\n[3/5] deploy ChainlinkComputeTaskAdapter ...");
  const compute = await deployContract(deployer, compiled, COMPUTE_ADAPTER_KEY, [
    { type: "address", value: linkToken },
    { type: "address", value: operator },
    { type: "bytes32", value: computeJobId },
    { type: "uint256", value: fee },
    { type: "address", value: main.contractAddress },
  ]);
  console.log("compute adapter:", compute.contractAddress);

  console.log("\n[4/5] wire adapters into MainOracleRouter ...");
  const mainAbi = compiled.contracts[MAIN_CONTRACT_KEY].abi;
  await callMethod(
    deployer,
    main.contractAddress,
    mainAbi,
    "setAdapters",
    [data.contractAddress, compute.contractAddress]
  );

  console.log("\n[5/5] authorize chainlink node writer (optional) ...");
  if (nodeAddress) {
    const dataAbi = compiled.contracts[DATA_ADAPTER_KEY].abi;
    const computeAbi = compiled.contracts[COMPUTE_ADAPTER_KEY].abi;
    await callMethod(
      deployer,
      data.contractAddress,
      dataAbi,
      "setWriter",
      [nodeAddress, true]
    );
    await callMethod(
      deployer,
      compute.contractAddress,
      computeAbi,
      "setWriter",
      [nodeAddress, true]
    );
    console.log("writer enabled:", nodeAddress);
  } else {
    console.log("skip: chainlinkNodeAddress not found");
  }

  const payload = {
    network: {
      rpcUrl: RPC_URL,
      deployer,
      chainId: await rpcCall("eth_chainId", []),
    },
    chainlink: {
      linkToken,
      operator,
      nodeAddress: nodeAddress || null,
      dataJobId,
      computeJobId,
      feeWei: fee,
    },
    contracts: {
      mainRouter: main.contractAddress,
      dataTaskAdapter: data.contractAddress,
      computeTaskAdapter: compute.contractAddress,
    },
    tx: {
      deployMain: main.txHash,
      deployData: data.txHash,
      deployCompute: compute.txHash,
    },
    timestamp: new Date().toISOString(),
  };
  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(payload, null, 2));
  console.log(`\n✅ done. written: ${OUTPUT_PATH}`);
}

main().catch((error) => {
  console.error("❌ failed:", error.message);
  process.exit(1);
});
