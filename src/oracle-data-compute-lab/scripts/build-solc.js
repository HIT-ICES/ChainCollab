import fs from "fs";
import path from "path";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
function loadSolc() {
  const candidates = ["solc", "hardhat/node_modules/solc"];
  for (const name of candidates) {
    try {
      return require(name);
    } catch (_err) {
      // Try next candidate.
    }
  }
  throw new Error(
    "solc module not found. Run `npm install` in oracle-data-compute-lab first."
  );
}
const solc = loadSolc();

const contractsDir = path.resolve("contracts");
const outDir = path.resolve("build");
const targets = [
  { source: "SlotRegistry.sol", contract: "SlotRegistry" },
  { source: "DataOracleHub.sol", contract: "DataOracleHub" },
  { source: "ComputeOracleHub.sol", contract: "ComputeOracleHub" },
  { source: "DataAggregationLab.sol", contract: "DataAggregationLab" },
  { source: "ComputeCostLab.sol", contract: "ComputeCostLab" }
];

function loadSources() {
  const entries = fs.readdirSync(contractsDir).filter((f) => f.endsWith(".sol"));
  const sources = {};
  for (const filename of entries) {
    const full = path.join(contractsDir, filename);
    sources[filename] = { content: fs.readFileSync(full, "utf-8") };
  }
  return sources;
}

function main() {
  const input = {
    language: "Solidity",
    sources: loadSources(),
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      },
      outputSelection: {
        "*": {
          "*": ["abi", "evm.bytecode.object"]
        }
      }
    }
  };

  const output = JSON.parse(solc.compile(JSON.stringify(input)));
  if (output.errors?.length) {
    const fatal = output.errors.filter((e) => e.severity === "error");
    for (const e of output.errors) {
      console.log(e.formattedMessage);
    }
    if (fatal.length > 0) {
      process.exit(1);
    }
  }

  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  for (const target of targets) {
    const contract = output.contracts?.[target.source]?.[target.contract];
    if (!contract) {
      throw new Error(`compilation output missing: ${target.contract}`);
    }
    const outFile = path.resolve(`build/${target.contract}.json`);
    fs.writeFileSync(
      outFile,
      JSON.stringify(
        {
          contractName: target.contract,
          abi: contract.abi,
          bytecode: `0x${contract.evm.bytecode.object}`
        },
        null,
        2
      )
    );
    console.log(`build artifact generated: ${outFile}`);
  }
}

main();
