from __future__ import annotations

import json
import subprocess

NODE_CALL_SCRIPT = r"""
const fs = require('fs');
const http = require('http');
const { URL } = require('url');

function rpcCall(rpcUrl, method, params) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({ jsonrpc: '2.0', method, params, id: 1 });
    const rpc = new URL(rpcUrl);
    const options = {
      hostname: rpc.hostname,
      port: rpc.port || (rpc.protocol === 'https:' ? 443 : 80),
      path: rpc.pathname === '' ? '/' : rpc.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
      },
    };
    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        const response = JSON.parse(data);
        if (response.error) reject(new Error(response.error.message));
        else resolve(response.result);
      });
    });
    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

async function main() {
  const input = JSON.parse(fs.readFileSync(0, 'utf8'));
  const compiled = JSON.parse(fs.readFileSync(input.compiledPath, 'utf8'));
  const contractKey = `contracts/${input.contractName}.sol:${input.contractName}`;
  const abi = compiled.contracts[contractKey]?.abi;
  if (!abi) {
    throw new Error(`Missing ABI for ${contractKey}`);
  }
  const fn = abi.find((item) => item.type === 'function' && item.name === input.method);
  if (!fn) {
    throw new Error(`Missing ABI for method ${input.method}`);
  }
  const Web3EthAbi = require('web3-eth-abi');
  const data = Web3EthAbi.encodeFunctionCall(fn, input.args);
  if (input.mode === 'send') {
    const accounts = await rpcCall(input.rpcUrl, 'eth_accounts', []);
    const from = input.from || accounts[0];
    const txHash = await rpcCall(input.rpcUrl, 'eth_sendTransaction', [{
      from,
      to: input.contractAddress,
      data,
      gas: '0x' + (input.gas || 5000000).toString(16),
    }]);
    console.log(JSON.stringify({ txHash }));
    return;
  }
  const result = await rpcCall(input.rpcUrl, 'eth_call', [{
    to: input.contractAddress,
    data,
  }, 'latest']);
  console.log(JSON.stringify({ result }));
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
"""


def execute_dmn_contract_call(
    *,
    compiled_path: str,
    contract_name: str,
    contract_address: str,
    method: str,
    args: list,
    mode: str,
    rpc_url: str,
    from_address=None,
    gas=5000000,
) -> dict:
    payload = {
        "compiledPath": compiled_path,
        "contractName": contract_name,
        "contractAddress": contract_address,
        "method": method,
        "args": args,
        "mode": "send" if mode == "invoke" else "call",
        "rpcUrl": rpc_url,
        "from": from_address,
        "gas": gas,
    }

    result = subprocess.run(
        ["node", "-e", NODE_CALL_SCRIPT],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "DMN contract call failed")
    try:
        return json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"raw": result.stdout.strip()}
