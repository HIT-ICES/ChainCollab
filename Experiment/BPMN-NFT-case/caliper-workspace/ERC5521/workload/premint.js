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

// -------------------- token1: batch mint NO references --------------------
class Token1PremintWorkload extends WorkloadModuleBase {
  async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
    await super.initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext);

    this.runId = this.roundArguments.runId;
    this.limit = parseInt(this.roundArguments.token1Count, 10);
    this.tokenURI = this.roundArguments.tokenURI || 'www.google.com';
    this.instanceID = String(this.roundArguments.instanceID ?? '0');
    this.invokerIdentity = this.roundArguments.invokerIdentity || 'user1';

    // You can override contractFunction if your ERC5521 uses another name
    this.contractFunction = this.roundArguments.contractFunction || 'SafeMint';

    console.log('[TOKEN1-PREMINT]', __filename, 'runId=', this.runId, 'limit=', this.limit);

    this.poolDir = resolvePoolDir(this.runId, this.roundArguments.poolBaseDir);
    fs.mkdirSync(this.poolDir, { recursive: true });

    // token1 manifest (so token2 round can read it)
    this.token1Path = path.join(this.poolDir, 'token1_ids.txt');
    this.token1LockPath = path.join(this.poolDir, 'token1_ids.lock');
    this.token1ReadyPath = path.join(this.poolDir, 'token1_ids.ready');
    initManifestOnce(this.token1Path, this.token1ReadyPath, path.join(this.poolDir, 'token1_ids.init.lock'));

    // Counter for token1 premint
    this.counterPath = path.join(this.poolDir, 'counter_token1.txt');
    this.lockPath = path.join(this.poolDir, 'counter_token1.lock');
    this.readyPath = path.join(this.poolDir, 'counter_token1.ready');
    resetCounterOnce(this.counterPath, this.readyPath, path.join(this.poolDir, 'counter_token1.init.lock'));

    this.buf = [];
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

    this.buf.push(tokenId);
    if (this.buf.length >= 200) {
      appendLinesLocked(this.token1Path, this.token1LockPath, this.buf);
      this.buf = [];
    }
  }

  async cleanupWorkloadModule() {
    appendLinesLocked(this.token1Path, this.token1LockPath, this.buf);
    await super.cleanupWorkloadModule();
  }
}

module.exports.createWorkloadModule = () => new Token1PremintWorkload();
