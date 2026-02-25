const fs = require("fs");
const path = require("path");
const solc = require("solc");
const { BUILD_DIR, ROOT, ensureDir, writeJson } = require("./common");

const CONTRACTS_DIR = path.join(ROOT, "contracts");

function gatherSources() {
  const files = fs
    .readdirSync(CONTRACTS_DIR)
    .filter((f) => f.endsWith(".sol"))
    .sort();

  const sources = {};
  for (const file of files) {
    const full = path.join(CONTRACTS_DIR, file);
    sources[file] = { content: fs.readFileSync(full, "utf-8") };
  }
  return sources;
}

function main() {
  ensureDir(BUILD_DIR);

  const input = {
    language: "Solidity",
    sources: gatherSources(),
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
  const errors = output.errors || [];
  const hardErrors = errors.filter((e) => e.severity === "error");

  for (const err of errors) {
    const prefix = err.severity === "error" ? "[ERROR]" : "[WARN]";
    console.log(`${prefix} ${err.formattedMessage.trim()}`);
  }

  if (hardErrors.length > 0) {
    process.exit(1);
  }

  let count = 0;
  for (const [source, contracts] of Object.entries(output.contracts || {})) {
    for (const [name, artifact] of Object.entries(contracts)) {
      const payload = {
        contractName: name,
        source,
        abi: artifact.abi,
        bytecode: artifact.evm.bytecode.object
      };
      writeJson(path.join(BUILD_DIR, `${name}.json`), payload);
      count += 1;
    }
  }

  console.log(`build ok: ${count} contracts -> ${BUILD_DIR}`);
}

main();
