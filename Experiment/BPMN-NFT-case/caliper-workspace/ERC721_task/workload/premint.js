'use strict';

const fs = require('fs');
const path = require('path');
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');

// ---------- helpers (v8: safe init + per-tx allocation) ----------
// Goals:
// - No "workerIndex===0" assumptions (late worker0 must NOT reset mid-round)
// - No batch reservation (prevents "reserved but never submitted" stalls)
// - Deterministic, filesystem-only coordination for Caliper local workers
//
// Important usage rule:
// - Use a fresh runId each run (recommended), OR delete token-pools/<runId>/ before rerunning.
//
// poolDir = (poolBaseDir || <workload_dir>/..)/token-pools/<runId>

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
    // If already initialized, return immediately; otherwise wait.
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


class PremintPoolsWorkload extends WorkloadModuleBase {
  async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
    await super.initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext);

    this.runId = this.roundArguments.runId;
    this.prepTransferCount = parseInt(this.roundArguments.prepTransferCount, 10);
    this.prepBurnCount = parseInt(this.roundArguments.prepBurnCount, 10);
    this.limit = this.prepTransferCount + this.prepBurnCount;

    console.log('[PREMINT]', __filename, 'runId=', this.runId, 'limit=', this.limit);

    this.poolDir = resolvePoolDir(this.runId, this.roundArguments.poolBaseDir);
    fs.mkdirSync(this.poolDir, { recursive: true });

    // Manifest for later rounds
    this.mintedPath = path.join(this.poolDir, 'minted_ids.txt');
    this.mintedLockPath = path.join(this.poolDir, 'minted_ids.lock');
    this.mintedReadyPath = path.join(this.poolDir, 'minted_ids.ready');
    initManifestOnce(this.mintedPath, this.mintedReadyPath, path.join(this.poolDir, 'minted_ids.init.lock'));

    // Counter for premint
    this.counterPath = path.join(this.poolDir, 'counter_premint.txt');
    this.lockPath = path.join(this.poolDir, 'counter_premint.lock');
    this.readyPath = path.join(this.poolDir, 'counter_premint.ready');
    resetCounterOnce(this.counterPath, this.readyPath, path.join(this.poolDir, 'counter_premint.init.lock'));

    this.buf = [];
  }

  async submitTransaction() {
    const idx = allocateNextIndex(this.counterPath, this.lockPath, this.limit);
    if (idx === null) {
      // Caliper may still call submitTransaction a few times while stopping; safe no-op.
      return;
    }

    const channel = this.roundArguments.channel;
    const contractId = this.roundArguments.contractId;
    const tokenURI = 'www.google.com';

    let tokenId, invokerIdentity;
    if (idx < this.prepTransferCount) {
      tokenId = `${this.runId}-prepT-${idx}-5`;
      invokerIdentity = 'user1';
    } else {
      const bIdx = idx - this.prepTransferCount;
      tokenId = `${this.runId}-prepB-${bIdx}-5`;
      invokerIdentity = 'user2';
    }

    await this.sutAdapter.sendRequests({
      channel,
      contractId,
      contractFunction: 'Activity_0i3c0p3_Continue',
      contractArguments: [tokenId,'0'],
      invokerIdentity
    });

    this.buf.push(tokenId);
    if (this.buf.length >= 200) {
      appendLinesLocked(this.mintedPath, this.mintedLockPath, this.buf);
      this.buf = [];
    }
  }

  async cleanupWorkloadModule() {
    appendLinesLocked(this.mintedPath, this.mintedLockPath, this.buf);
    await super.cleanupWorkloadModule();
  }
}

module.exports.createWorkloadModule = () => new PremintPoolsWorkload();
