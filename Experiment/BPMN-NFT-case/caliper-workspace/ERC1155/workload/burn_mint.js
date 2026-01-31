'use strict';

const fs = require('fs');
const path = require('path');
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');

// ---------- helpers (v8: safe init + per-tx allocation) ----------

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

function loadLines(filePath) {
  if (!fs.existsSync(filePath)) return [];
  const raw = fs.readFileSync(filePath, 'utf8');
  return raw.split('\n').map(s => s.trim()).filter(Boolean);
}

class BurnMintWorkload extends WorkloadModuleBase {
  async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
    await super.initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext);

    this.runId = this.roundArguments.runId;

    // 复用 burnCount 这个参数名（跟 burn.js 一致），你也可以在 yaml 里写 burnMintCount 再改这里
    this.limit = parseInt(this.roundArguments.burnCount, 10);

    // mint 默认 invoker 是 user1（mint.js 里就是 user1）:contentReference[oaicite:3]{index=3}
    this.invokerIdentity = this.roundArguments.invokerIdentity || 'user1';

    console.log('[BURN-MINT]', __filename, 'runId=', this.runId, 'limit=', this.limit);

    this.poolDir = resolvePoolDir(this.runId, this.roundArguments.poolBaseDir);
    fs.mkdirSync(this.poolDir, { recursive: true });

    this.mintedPath = path.join(this.poolDir, 'minted_ids.txt');
    waitForFileExists(path.join(this.poolDir, 'minted_ids.ready'));

    const all = loadLines(this.mintedPath);

    // ✅ 关键：只烧掉 mint.js 创建的 token（包含 -mint-）
    this.pool = all.filter(id => id.includes('-mint-'));

    if (this.pool.length < this.limit) {
      throw new Error(`burn-mint pool not enough: need ${this.limit}, got ${this.pool.length}. (mint success?)`);
    }

    // 用独立计数器，避免与原 burn.js 的 counter_burn 冲突
    this.counterPath = path.join(this.poolDir, 'counter_burn_mint.txt');
    this.lockPath = path.join(this.poolDir, 'counter_burn_mint.lock');
    this.readyPath = path.join(this.poolDir, 'counter_burn_mint.ready');
    resetCounterOnce(this.counterPath, this.readyPath, path.join(this.poolDir, 'counter_burn_mint.init.lock'));
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
      contractFunction: 'Activity_0jgcjkn',
      contractArguments: [tokenId, '0'],
      invokerIdentity: this.invokerIdentity
    });
  }
}

module.exports.createWorkloadModule = () => new BurnMintWorkload();
