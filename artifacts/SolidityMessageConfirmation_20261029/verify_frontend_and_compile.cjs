const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const solc = require('solc');
const root = '/home/shenxz-lab/code/ChainCollab';
const evidence = path.join(root, 'artifacts/SolidityMessageConfirmation_20261029');
const ts = require(path.join(root, 'src/front/node_modules/typescript'));
const source = fs.readFileSync(path.join(root, 'src/front/src/views/BPMN/Execution/SvgComponent/index.tsx'), 'utf8');
const start = source.indexOf('const getEthereumActionConfig =');
const end = source.indexOf('const getEthereumActionKey =', start);
const selected = source.slice(start, end) + '\nglobalThis.actionConfig = getEthereumActionConfig;';
const sandbox = {
  buildEthereumMethodPayload: (_method, id) => ({ instanceId: id })
};
vm.createContext(sandbox);
vm.runInContext(ts.transpileModule(selected, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText, sandbox);
const methods = { M_Send: { name: 'M_Send' }, M_Complete: { name: 'M_Complete' } };
const config = state => sandbox.actionConfig({ type: 'message', state, MessageID: 'M' }, 7, methods, {});
assert.equal(config(1).method, 'M_Send');
assert.equal(config(2).method, 'M_Complete');
assert.equal(config(2).payload.instanceId, 7);
assert.equal(config(3), null);
assert.equal(sandbox.actionConfig({ type: 'message', state: 2, MessageID: 'M' }, 7, { M_Send: methods.M_Send }, {}), null);
fs.writeFileSync(path.join(evidence, 'frontend_routing.json'), JSON.stringify({ status: 'PASS', checks: ['READY routes to Send', 'WAITING routes to Complete', 'Correct instance payload', 'COMPLETED offers no action', 'Legacy ABI without Complete offers no invalid confirmation'], scope: 'Actual TS action-selection function transpiled in isolation; payload builder stubbed; full frontend also checked with tsc' }, null, 2) + '\n');
function files(dir) { return fs.readdirSync(dir, { withFileTypes: true }).flatMap(item => item.isDirectory() ? files(path.join(dir, item.name)) : [path.join(dir, item.name)]); }
const sources = Object.fromEntries(files(path.join(evidence, 'generated')).filter(p => p.endsWith('.sol')).map(p => [path.relative(evidence, p), { content: fs.readFileSync(p, 'utf8') }]));
const typeCheck = JSON.parse(solc.compile(JSON.stringify({ language: 'Solidity', sources, settings: { outputSelection: { '*': { '*': ['abi'] } } } })));
const errors = (typeCheck.errors || []).filter(e => e.severity === 'error');
fs.writeFileSync(path.join(evidence, 'compiler_typecheck.json'), JSON.stringify({ sources: Object.keys(sources).length, compiler: solc.version(), errors, warnings: (typeCheck.errors || []).filter(e => e.severity !== 'error') }, null, 2) + '\n');
assert.equal(errors.length, 0, errors.map(e => e.formattedMessage).join('\n'));
const bytecodeResults = [];
for (const key of Object.keys(sources).filter(p => p.includes('/SupplyChainPaper/'))) {
  const compiled = JSON.parse(solc.compile(JSON.stringify({ language: 'Solidity', sources: { [key]: sources[key] }, settings: { optimizer: { enabled: true, runs: 200 }, viaIR: true, evmVersion: 'shanghai', outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object'] } } } })));
  const errs = (compiled.errors || []).filter(e => e.severity === 'error');
  bytecodeResults.push({ source: key, errors: errs, bytecodeBytes: Object.fromEntries(Object.entries(compiled.contracts?.[key] || {}).map(([name, value]) => [name, value.evm.bytecode.object.length / 2])) });
  assert.equal(errs.length, 0, errs.map(e => e.formattedMessage).join('\n'));
}
fs.writeFileSync(path.join(evidence, 'supplychain_bytecode.json'), JSON.stringify({ status: 'PASS', compiler: solc.version(), optimizerRuns: 200, viaIR: true, evmVersion: 'shanghai', results: bytecodeResults }, null, 2) + '\n');
console.log(JSON.stringify({ frontend: 'PASS', typechecked: Object.keys(sources).length, supplyChainBytecodeCompiled: bytecodeResults.length }));
