'use strict';

const fs = require('fs');
const path = require('path');
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');

// ---------- helpers (copied from your premint.js style) ----------
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

function tryCreateInitLock(initLockPath) {
  try {
    return fs.openSync(initLockPath, 'wx');
  } catch (e) {
    return null;
  }
}

function closeFd(fd) {
  if (fd !== null) {
    try { fs.closeSync(fd); } catch (e) {}
  }
}

function resetCounterOnce(counterPath, readyPath, initLockPath) {
  const fd = tryCreateInitLock(initLockPath);
  if (fd !== null) {
    try {
      try { fs.unlinkSync(readyPath); } catch (e) {}
      fs.writeFileSync(counterPath, '0', 'utf8');
      fs.writeFileSync(readyPath, String(Date.now()), 'utf8');
    } finally {
      closeFd(fd);
    }
  } else {
    if (fs.existsSync(readyPath)) return;
    waitForFileExists(readyPath);
  }
}

function acquireFileLock(lockPath) {
  while (true) {
    try {
      const fd = fs.openSync(lockPath, 'wx');
      return fd;
    } catch (e) {
      sleepMs(10);
    }
  }
}

function releaseFileLock(lockPath, fd) {
  try { fs.closeSync(fd); } catch (e) {}
  try { fs.unlinkSync(lockPath); } catch (e) {}
}

function ensureCounterFile(counterPath) {
  if (!fs.existsSync(counterPath)) {
    fs.writeFileSync(counterPath, '0', 'utf8');
  }
}

function allocateNextIndex(counterPath, lockPath, limit) {
  const fd = acquireFileLock(lockPath);
  try {
    ensureCounterFile(counterPath);
    const cur = parseInt((fs.readFileSync(counterPath, 'utf8').trim() || '0'), 10);
    if (cur >= limit) return null;
    fs.writeFileSync(counterPath, String(cur + 1), 'utf8');
    return cur;
  } finally {
    releaseFileLock(lockPath, fd);
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

function appendLinesLocked(filePath, lockPath, lines) {
  if (!lines || lines.length === 0) return;
  const fd = acquireFileLock(lockPath);
  try {
    fs.appendFileSync(filePath, lines.join('\n') + '\n', 'utf8');
  } finally {
    releaseFileLock(lockPath, fd);
  }
}

function initManifestOnce(manifestPath, readyPath, initLockPath) {
  const fd = tryCreateInitLock(initLockPath);
  if (fd !== null) {
    try {
      try { fs.unlinkSync(readyPath); } catch (e) {}
      fs.writeFileSync(manifestPath, '', 'utf8');
      fs.writeFileSync(readyPath, String(Date.now()), 'utf8');
    } finally {
      closeFd(fd);
    }
  } else {
    if (fs.existsSync(readyPath)) return;
    waitForFileExists(readyPath);
  }
}

// -------------------- token2: batch mint WITH references to token1 (batch b) --------------------
class Token2RefMintWorkload_B extends WorkloadModuleBase {
  async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
    await super.initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext);

    this.runId = this.roundArguments.runId;
    this.tokenURI = this.roundArguments.tokenURI || 'www.google.com';
    this.instanceID = String(this.roundArguments.instanceID ?? '0');
    this.invokerIdentity = this.roundArguments.invokerIdentity || 'user1';

    // You can override contractFunction if your ERC5521 uses another name
    this.contractFunction = this.roundArguments.contractFunction || 'SafeMint';

    this.poolDir = resolvePoolDir(this.runId, this.roundArguments.poolBaseDir);
    fs.mkdirSync(this.poolDir, { recursive: true });

    // Read token1 pool (created by token1-premint round)
    this.token1Path = path.join(this.poolDir, 'token1_ids_b.txt');
    this.token1ReadyPath = path.join(this.poolDir, 'token1_ids_b.ready');
    waitForFileExists(this.token1ReadyPath); // ensure token1 manifest is initialized

    this.token1List = loadLines(this.token1Path);
    if (this.token1List.length === 0) {
      throw new Error(`[TOKEN2-REFMINT-B] token1 list is empty: ${this.token1Path}`);
    }

    // token2Count, but we can only "顺序引用" up to token1List.length (unless wrap enabled)
    this.wrap = String(this.roundArguments.wrap ?? 'false') === 'true';
    const asked = parseInt(this.roundArguments.token2Count, 10);
    this.limit = this.wrap ? asked : Math.min(asked, this.token1List.length);

    console.log('[TOKEN2-REFMINT-B]', __filename, 'runId=', this.runId, 'token2Asked=', asked, 'limit=', this.limit, 'token1=', this.token1List.length, 'wrap=', this.wrap);

    // token2 manifest (optional, for later rounds)
    this.token2Path = path.join(this.poolDir, 'token2_ids_b.txt');
    this.token2LockPath = path.join(this.poolDir, 'token2_ids_b.lock');
    this.token2ReadyPath = path.join(this.poolDir, 'token2_ids_b.ready');
    initManifestOnce(this.token2Path, this.token2ReadyPath, path.join(this.poolDir, 'token2_ids_b.init.lock'));

    // Counter for token2 mint
    this.counterPath = path.join(this.poolDir, 'counter_token2_b.txt');
    this.lockPath = path.join(this.poolDir, 'counter_token2_b.lock');
    this.readyPath = path.join(this.poolDir, 'counter_token2_b.ready');
    resetCounterOnce(this.counterPath, this.readyPath, path.join(this.poolDir, 'counter_token2_b.init.lock'));

    // refChaincodeName: "same chaincode" by default
    this.refChaincodeName = this.roundArguments.refChaincodeName || null;

    this.buf = [];
  }

  async submitTransaction() {
    const idx = allocateNextIndex(this.counterPath, this.lockPath, this.limit);
    if (idx === null) return;

    const channel = this.roundArguments.channel;
    const contractId = this.roundArguments.contractId;

    // token2 id
    const token2Id = `${this.runId}-token2-b-${idx}-5`;

    // "依次引用"：token2[idx] -> token1[idx] (or wrap)
    const token1Id = this.wrap
      ? this.token1List[idx % this.token1List.length]
      : this.token1List[idx];

    const refCC = this.refChaincodeName || contractId; // same chaincode by default
    const chaincodeNameJson = JSON.stringify([refCC]);
    const tokenIdsJson = JSON.stringify([[token1Id]]);

    await this.sutAdapter.sendRequests({
      channel,
      contractId,
      contractFunction: this.contractFunction,
      contractArguments: [token2Id, this.tokenURI, this.instanceID, chaincodeNameJson, tokenIdsJson],
      invokerIdentity: this.invokerIdentity
    });

    this.buf.push(token2Id);
    if (this.buf.length >= 200) {
      appendLinesLocked(this.token2Path, this.token2LockPath, this.buf);
      this.buf = [];
    }
  }

  async cleanupWorkloadModule() {
    appendLinesLocked(this.token2Path, this.token2LockPath, this.buf);
    await super.cleanupWorkloadModule();
  }
}

module.exports.createWorkloadModule = () => new Token2RefMintWorkload_B();
