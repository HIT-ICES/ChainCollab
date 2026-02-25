const axios = require('axios');
const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
require('dotenv').config({ path: path.join(ROOT_DIR, '.env') });

const CHAINLINK_URL = process.env.CHAINLINK_URL || 'http://localhost:6687';
const CHAINLINK_EMAIL = process.env.CHAINLINK_EMAIL || 'admin@chain.link';
const CHAINLINK_PASSWORD = process.env.CHAINLINK_PASSWORD || 'change-me-strong';

const API_ENDPOINTS = {
  LOGIN: '/sessions',
  JOBS: '/v2/jobs',
};

function readJson(filePath) {
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (_) {
    return null;
  }
}

class ChainlinkJobManager {
  constructor() {
    this.authToken = null;
  }

  async login() {
    console.log('🔐 正在登录 Chainlink 节点...');
    console.log('📍 节点地址:', CHAINLINK_URL);
    const response = await axios.post(`${CHAINLINK_URL}${API_ENDPOINTS.LOGIN}`, {
      email: CHAINLINK_EMAIL,
      password: CHAINLINK_PASSWORD,
    });
    if (response.headers['set-cookie']) {
      this.authToken = response.headers['set-cookie'].join('; ');
      console.log('✅ 登录成功');
    } else {
      throw new Error('未获取到会话 Cookie');
    }
  }

  async deleteJob(jobId) {
    console.log(`🗑️  正在删除 Job ${jobId}...`);
    const response = await axios.delete(`${CHAINLINK_URL}${API_ENDPOINTS.JOBS}/${jobId}`, {
      headers: {
        'Content-Type': 'application/json',
        Cookie: this.authToken,
      },
    });

    if (response.status === 204) {
      console.log('✅ Job 删除成功!');
      return true;
    }
    throw new Error(`请求失败，状态码: ${response.status}`);
  }

  async listJobs() {
    const response = await axios.get(`${CHAINLINK_URL}${API_ENDPOINTS.JOBS}`, {
      headers: {
        'Content-Type': 'application/json',
        Cookie: this.authToken,
      },
    });

    if (response.status === 200) {
      return response.data.data || [];
    }
    throw new Error(`请求失败，状态码: ${response.status}`);
  }
}

function resolveJobIdInput() {
  const argId = process.argv[2];
  if (argId) return argId;

  const deploymentPath = path.join(ROOT_DIR, 'deployment', 'chainlink-deployment.json');
  const deployment = readJson(deploymentPath);
  return (
    process.env.OCR_WRITER_JOB_ID ||
    process.env.OCR_WRITER_EXTERNAL_JOB_ID ||
    deployment?.ocrWriterJobId ||
    deployment?.ocrWriterExternalJobId ||
    null
  );
}

async function main() {
  console.log('🎯 OCR Writer Job 删除工具');
  console.log('='.repeat(50));
  console.log('');

  const jobIdInput = resolveJobIdInput();
  if (!jobIdInput) {
    console.error('❌ 未提供 Job ID，请传入内部 ID 或外部 ID');
    console.log(
      '用法: node features/04-dmn-ocr/delete-ocr-writer-job.js <jobInternalId|externalJobId>'
    );
    process.exit(1);
  }

  const jobManager = new ChainlinkJobManager();
  await jobManager.login();

  let resolvedJobId = jobIdInput;
  let resolvedExternalId = null;
  try {
    const jobs = await jobManager.listJobs();
    const found = jobs.find((job) => job?.attributes?.externalJobID === jobIdInput);
    if (found) {
      resolvedJobId = found.id;
      resolvedExternalId = found.attributes.externalJobID;
      console.log('✅ 已解析外部 ID 对应的内部 ID:', resolvedJobId);
    }
  } catch (error) {
    console.warn('⚠️  无法获取 Job 列表，继续尝试用提供的 ID 删除');
  }

  try {
    await jobManager.deleteJob(resolvedJobId);
  } catch (error) {
    console.error('❌ Job 删除失败:', error.message);
    if (error.response) {
      console.error('响应状态:', error.response.status);
      console.error('响应数据:', error.response.data);
    }
    process.exit(1);
  }

  const deploymentPath = path.join(ROOT_DIR, 'deployment', 'chainlink-deployment.json');
  if (fs.existsSync(deploymentPath)) {
    const deployment = readJson(deploymentPath) || {};
    let changed = false;

    if (deployment.ocrWriterJobId === resolvedJobId) {
      delete deployment.ocrWriterJobId;
      changed = true;
    }
    if (
      deployment.ocrWriterExternalJobId === jobIdInput ||
      (resolvedExternalId && deployment.ocrWriterExternalJobId === resolvedExternalId)
    ) {
      delete deployment.ocrWriterExternalJobId;
      changed = true;
    }

    if (changed) {
      fs.writeFileSync(deploymentPath, JSON.stringify(deployment, null, 2));
      console.log('✅ 已清理 deployment/chainlink-deployment.json 中的 ocrWriter 记录');
    }
  }

  console.log('');
  console.log('🎉 OCR Writer Job 删除成功！');
}

if (require.main === module) {
  main().catch((err) => {
    console.error('❌ 操作失败:', err.message);
    process.exit(1);
  });
}

