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

// persistent init-lock (do NOT delete it)
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

// short-lived lock for atomic allocation
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

// Allocate ONE index per tx. Returns null if exhausted.
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

function appendLinesLocked(filePath, lockPath, lines) {
  if (!lines || lines.length === 0) return;
  const fd = acquireFileLock(lockPath);
  try {
    fs.appendFileSync(filePath, lines.join('\n') + '\n', 'utf8');
  } finally {
    releaseFileLock(lockPath, fd);
  }
}

// Initialize manifest once for this runId (persistent init-lock)
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

// -------------------- token1: batch mint NO references (two batches) --------------------
class Token1PremintWorkload extends WorkloadModuleBase {
  async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
    await super.initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext);

    this.runId = this.roundArguments.runId;

    // two batches
    this.batchACount = parseInt(this.roundArguments.token1CountA, 10);
    this.batchBCount = parseInt(this.roundArguments.token1CountB, 10);
    this.limit = this.batchACount + this.batchBCount;

    this.tokenURI = this.roundArguments.tokenURI || 'www.google.com';
    this.instanceID = String(this.roundArguments.instanceID ?? '0');
    this.invokerIdentity = this.roundArguments.invokerIdentity || 'user1';

    // You can override contractFunction if your ERC5521 uses another name
    this.contractFunction = this.roundArguments.contractFunction || 'SafeMint';

    console.log(
      '[TOKEN1-PREMINT]',
      __filename,
      'runId=',
      this.runId,
      'batchA=',
      this.batchACount,
      'batchB=',
      this.batchBCount,
      'total=',
      this.limit
    );

    this.poolDir = resolvePoolDir(this.runId, this.roundArguments.poolBaseDir);
    fs.mkdirSync(this.poolDir, { recursive: true });

    // token1 manifests (split)
    this.token1APath = path.join(this.poolDir, 'token1_ids_a.txt');
    this.token1ALockPath = path.join(this.poolDir, 'token1_ids_a.lock');
    this.token1AReadyPath = path.join(this.poolDir, 'token1_ids_a.ready');
    initManifestOnce(this.token1APath, this.token1AReadyPath, path.join(this.poolDir, 'token1_ids_a.init.lock'));

    this.token1BPath = path.join(this.poolDir, 'token1_ids_b.txt');
    this.token1BLockPath = path.join(this.poolDir, 'token1_ids_b.lock');
    this.token1BReadyPath = path.join(this.poolDir, 'token1_ids_b.ready');
    initManifestOnce(this.token1BPath, this.token1BReadyPath, path.join(this.poolDir, 'token1_ids_b.init.lock'));

    // Counter for token1 premint (covers A+B together)
    this.counterPath = path.join(this.poolDir, 'counter_token1.txt');
    this.lockPath = path.join(this.poolDir, 'counter_token1.lock');
    this.readyPath = path.join(this.poolDir, 'counter_token1.ready');
    resetCounterOnce(this.counterPath, this.readyPath, path.join(this.poolDir, 'counter_token1.init.lock'));

    this.bufA = [];
    this.bufB = [];
  }

  async submitTransaction() {
    const idx = allocateNextIndex(this.counterPath, this.lockPath, this.limit);
    if (idx === null) return;

    const channel = this.roundArguments.channel;
    const contractId = this.roundArguments.contractId;

    // token1 id: sequential, unique under (runId, idx)
    const tokenId = `${this.runId}-token1-${idx}-5`;

    // No references: pass JSON empty arrays for []string and [][]string
    const chaincodeNameJson = '[]';
    const tokenIdsJson = '[]';

    await this.sutAdapter.sendRequests({
      channel,
      contractId,
      contractFunction: this.contractFunction,
      contractArguments: [tokenId, this.tokenURI, this.instanceID, chaincodeNameJson, tokenIdsJson],
      invokerIdentity: this.invokerIdentity
    });

    // split write: first A, then B
    if (idx < this.batchACount) {
      this.bufA.push(tokenId);
      if (this.bufA.length >= 200) {
        appendLinesLocked(this.token1APath, this.token1ALockPath, this.bufA);
        this.bufA = [];
      }
    } else {
      this.bufB.push(tokenId);
      if (this.bufB.length >= 200) {
        appendLinesLocked(this.token1BPath, this.token1BLockPath, this.bufB);
        this.bufB = [];
      }
    }
  }

  async cleanupWorkloadModule() {
    appendLinesLocked(this.token1APath, this.token1ALockPath, this.bufA);
    appendLinesLocked(this.token1BPath, this.token1BLockPath, this.bufB);
    await super.cleanupWorkloadModule();
  }
}

module.exports.createWorkloadModule = () => new Token1PremintWorkload();
