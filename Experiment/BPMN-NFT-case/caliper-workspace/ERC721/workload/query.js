'use strict';

const fs = require('fs');
const path = require('path');
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');

// tiny sleep (no async timers in tight loops)
function sleepMs(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function waitForFileExists(filePath, timeoutMs = 120000) {
  const start = Date.now();
  while (true) {
    if (fs.existsSync(filePath)) return;
    if (Date.now() - start > timeoutMs) {
      throw new Error(`timeout waiting for ${filePath}`);
    }
    sleepMs(20);
  }
}

function resolvePoolDir(runId, poolBaseDir) {
  const base = poolBaseDir ? path.resolve(poolBaseDir) : path.resolve(__dirname, '..');
  return path.join(base, 'token-pools', runId);
}

function loadLines(filePath) {
  if (!fs.existsSync(filePath)) return [];
  const raw = fs.readFileSync(filePath, 'utf8');
  return raw.split('\n').map(s => s.trim()).filter(Boolean);
}

/**
 * Query-prepT-hot:
 * - Wait minted_ids.ready
 * - Read minted_ids.txt
 * - Pick ONE existing tokenId that contains poolTag (default "-prepT-")
 * - Every submitTransaction repeatedly queries that SAME tokenId
 *
 * This intentionally creates a "hot read" workload.
 */
class QueryPrepTHotWorkload extends WorkloadModuleBase {
  async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
    await super.initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext);

    this.runId = this.roundArguments.runId;
    this.poolTag = this.roundArguments.poolTag || '-prepT-';
    this.queryFunction = "OwnerOf";
    this.invokerIdentity = this.roundArguments.invokerIdentity || 'user1';

    this.poolDir = resolvePoolDir(this.runId, this.roundArguments.poolBaseDir);
    fs.mkdirSync(this.poolDir, { recursive: true });

    const readyPath = path.join(this.poolDir, 'minted_ids.ready');
    const mintedPath = path.join(this.poolDir, 'minted_ids.txt');

    // Ensure premint has finished creating the manifest
    waitForFileExists(readyPath);

    const ids = loadLines(mintedPath);
    const pool = ids.filter(id => id.includes(this.poolTag));

    if (!pool.length) {
      throw new Error(`No tokenId matched poolTag=${this.poolTag}. Check runId / premint outputs.`);
    }

    // Pick ONE token for all transactions in this worker.
    // If you want ALL workers to hit the same token, picking pool[0] is simplest.
    this.tokenId = pool[0];

    console.log('[QUERY-PREPTHOOK]',
      `runId=${this.runId}`,
      `poolTag=${this.poolTag}`,
      `pickedTokenId=${this.tokenId}`,
      `queryFunction=${this.queryFunction}`,
      `invoker=${this.invokerIdentity}`
    );
  }

  async submitTransaction() {
    const channel = this.roundArguments.channel;
    const contractId = this.roundArguments.contractId;

    await this.sutAdapter.sendRequests({
      channel,
      contractId,
      contractFunction: this.queryFunction,
      contractArguments: [this.tokenId],
      invokerIdentity: 'user1',
    });
  }
}

module.exports.createWorkloadModule = () => new QueryPrepTHotWorkload();
