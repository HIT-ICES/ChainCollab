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


class BurnWorkload extends WorkloadModuleBase {
  async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
    await super.initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext);

    this.runId = this.roundArguments.runId;
    this.limit = parseInt(this.roundArguments.burnCount, 10);

    console.log('[BURN]', __filename, 'runId=', this.runId, 'limit=', this.limit);

    this.poolDir = resolvePoolDir(this.runId, this.roundArguments.poolBaseDir);
    fs.mkdirSync(this.poolDir, { recursive: true });

    this.mintedPath = path.join(this.poolDir, 'minted_ids.txt');
    waitForFileExists(path.join(this.poolDir, 'minted_ids.ready'));

    const all = loadLines(this.mintedPath);
    this.pool = all.filter(id => id.includes('-prepB-'));
    if (this.pool.length < this.limit) {
      throw new Error(`burn pool not enough: need ${this.limit}, got ${this.pool.length}. (premint success?)`);
    }

    this.counterPath = path.join(this.poolDir, 'counter_burn.txt');
    this.lockPath = path.join(this.poolDir, 'counter_burn.lock');
    this.readyPath = path.join(this.poolDir, 'counter_burn.ready');
    resetCounterOnce(this.counterPath, this.readyPath, path.join(this.poolDir, 'counter_burn.init.lock'));
  }

  async submitTransaction() {
    const idx = allocateNextIndex(this.counterPath, this.lockPath, this.limit);
    if (idx === null) return;

    const tokenId = this.pool[idx];
    const channel = this.roundArguments.channel;
    const contractId = this.roundArguments.contractId;

    await this.sutAdapter.sendRequests({
      channel,
      contractId,
      contractFunction: 'Activity_0oqcguv',
      contractArguments: [tokenId,"0"],
      invokerIdentity: 'user2'
    });
  }
}

module.exports.createWorkloadModule = () => new BurnWorkload();
