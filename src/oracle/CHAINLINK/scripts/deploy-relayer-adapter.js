const fs = require("fs");
const http = require("http");
const { URL } = require("url");
const Web3EthAbi = require("web3-eth-abi");

const RPC_URL = process.env.RPC_URL || "http://localhost:8545";
const DEPLOYMENT_DIR = "deployment";
const COMPILED_PATH = `${DEPLOYMENT_DIR}/compiled.json`;
const OUTPUT_PATH = `${DEPLOYMENT_DIR}/relayer-adapter.json`;
const EXPECTED_DEPLOYER = (
  process.env.DEPLOYER_ACCOUNT ||
  process.env.ETH_SYSTEM_ACCOUNT ||
  ""
).toLowerCase();
const CONTRACT_KEY = "contracts/CrossChainAdapter.sol:CrossChainAdapter";

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

function ensureAddress(input) {
  const value = String(input || "").trim();
  if (!/^0x[a-fA-F0-9]{40}$/.test(value)) {
    throw new Error(`invalid relayer address: ${input}`);
  }
  return value;
}

function resolveRelayerSet(deployer) {
  const raw = String(process.env.RELAYER_SIGNERS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const relayers = raw.length > 0 ? raw.map(ensureAddress) : [ensureAddress(deployer)];

  const thresholdRaw = Number(process.env.RELAYER_THRESHOLD || 1);
  const threshold = Number.isFinite(thresholdRaw)
    ? Math.max(1, Math.floor(thresholdRaw))
    : 1;
  if (threshold > relayers.length) {
    throw new Error(
      `RELAYER_THRESHOLD ${threshold} exceeds relayer count ${relayers.length}`
    );
  }

  return { relayers, threshold };
}

function encodeConstructor(args) {
  if (!args || args.length === 0) return "";
  const types = args.map((a) => a.type);
  const values = args.map((a) => a.value);
  return Web3EthAbi.encodeParameters(types, values).slice(2);
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

async function main() {
  if (!fs.existsSync(COMPILED_PATH)) {
    throw new Error(`missing ${COMPILED_PATH}, run ./compile.sh first`);
  }
  const compiled = JSON.parse(fs.readFileSync(COMPILED_PATH, "utf8"));
  const contractData = (compiled.contracts || {})[CONTRACT_KEY];
  if (!contractData) {
    throw new Error(`contract not found in compiled.json: ${CONTRACT_KEY}`);
  }

  const accounts = await rpcCall("eth_accounts", []);
  const deployer = pickDeployer(accounts);
  const { relayers, threshold } = resolveRelayerSet(deployer);

  const bytecode = "0x" + contractData.bin;
  const constructorArgs = [
    { type: "address[]", value: relayers },
    { type: "uint256", value: String(threshold) },
  ];
  const data = bytecode + encodeConstructor(constructorArgs);

  console.log("RPC URL:", RPC_URL);
  console.log("deployer:", deployer);
  console.log("relayers:", relayers.join(", "));
  console.log("threshold:", threshold);

  const { txHash, receipt } = await sendTx(deployer, {
    data,
    gas: "0x" + (6000000).toString(16),
  });

  const payload = {
    network: {
      rpcUrl: RPC_URL,
      chainId: await rpcCall("eth_chainId", []),
      deployer,
    },
    contract: {
      name: "CrossChainAdapter",
      address: receipt.contractAddress,
      txHash,
    },
    relayers,
    threshold,
    timestamp: new Date().toISOString(),
  };

  if (!fs.existsSync(DEPLOYMENT_DIR)) {
    fs.mkdirSync(DEPLOYMENT_DIR, { recursive: true });
  }
  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(payload, null, 2));
  console.log(`✅ done. written: ${OUTPUT_PATH}`);
}

main().catch((error) => {
  console.error("❌ failed:", error.message);
  process.exit(1);
});
