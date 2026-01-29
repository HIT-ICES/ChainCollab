const axios = require('axios');
const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
require('dotenv').config({ path: path.join(ROOT_DIR, '.env') });

const CHAINLINK_URL = process.env.CHAINLINK_URL || 'http://localhost:6687';
const CHAINLINK_EMAIL = process.env.CHAINLINK_EMAIL || 'admin@chain.link';
const CHAINLINK_PASSWORD = process.env.CHAINLINK_PASSWORD || 'change-me-strong';

const JOB_SPEC_PATH = path.resolve(__dirname, 'job-spec-ocr-writer.toml');
const EI_FILE =
  process.env.EI_FILE ||
  path.join(ROOT_DIR, 'deployment', 'external-initiator.json');

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

  async createJob(jobSpec) {
    console.log('📝 正在创建 OCR Writer Job...');
    const response = await axios.post(
      `${CHAINLINK_URL}${API_ENDPOINTS.JOBS}`,
      { toml: jobSpec },
      {
        headers: {
          'Content-Type': 'application/json',
          Cookie: this.authToken,
        },
      }
    );
    if (response.status === 200 && response.data) {
      console.log('✅ Job 创建成功!');
      console.log('Job ID:', response.data.data.id);
      console.log('External Job ID:', response.data.data.attributes.externalJobID);
      return response.data.data;
    }
    throw new Error(`请求失败，状态码: ${response.status}`);
  }
}

async function main() {
  const externalJobId = process.env.EXTERNAL_JOB_ID || process.argv[3] || null;
  const dmnRequestDeployment = readJson(path.join(ROOT_DIR, 'deployment', 'deployment.json'));
  const dmnRequestAddress =
    process.env.DMN_REQUEST_CONTRACT_ADDRESS || dmnRequestDeployment?.contractAddress;
  const rawByHashUrl = process.env.DMN_RAW_BY_HASH_URL || process.argv[2];
  const eiInfo = readJson(EI_FILE);
  const eiName = process.env.EI_NAME || eiInfo?.name;

  if (!dmnRequestAddress) {
    console.error('❌ 缺少 DMN request 合约地址，请设置 DMN_REQUEST_CONTRACT_ADDRESS 或 deployment/deployment.json');
    process.exit(1);
  }
  if (!rawByHashUrl) {
    console.error('❌ 缺少 DMN raw by hash URL，请设置 DMN_RAW_BY_HASH_URL 或作为参数传入');
    console.log('用法: DMN_RAW_BY_HASH_URL=http://dmn-node1:8080/api/dmn/by-hash node features/04-dmn-ocr/create-ocr-writer-job.js');
    process.exit(1);
  }
  if (!eiName) {
    console.error('❌ 缺少 External Initiator 名称，请先运行 create-external-initiator.js');
    process.exit(1);
  }

  let jobSpecContent = fs.readFileSync(JOB_SPEC_PATH, 'utf8');
  if (externalJobId) {
    jobSpecContent = jobSpecContent.replace('<OCR_WRITER_JOB_EXTERNAL_ID>', externalJobId);
  } else {
    jobSpecContent = jobSpecContent.replace(/^externalJobID\s*=.*\n/m, '');
  }
  jobSpecContent = jobSpecContent.replace('<DMN_REQUEST_CONTRACT_ADDRESS>', dmnRequestAddress);
  jobSpecContent = jobSpecContent.replace('<DMN_RAW_BY_HASH_URL>', rawByHashUrl);
  jobSpecContent = jobSpecContent.replace('<EXTERNAL_INITIATOR_NAME>', eiName);
  jobSpecContent = jobSpecContent.replace(/\\"/g, '"');

  const jobManager = new ChainlinkJobManager();
  await jobManager.login();
  console.log('--- Final Job Spec ---');
  console.log(jobSpecContent);
  console.log('--- End Job Spec ---');
  const jobData = await jobManager.createJob(jobSpecContent);

  const deploymentPath = path.join(ROOT_DIR, 'deployment', 'chainlink-deployment.json');
  if (fs.existsSync(deploymentPath)) {
    const deploymentData = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
    deploymentData.ocrWriterJobId = jobData.id;
    deploymentData.ocrWriterExternalJobId = jobData.attributes.externalJobID;
    fs.writeFileSync(deploymentPath, JSON.stringify(deploymentData, null, 2));
    console.log('✅ 已写入 ocrWriterJobId 到 deployment/chainlink-deployment.json');
  }
}

if (require.main === module) {
  main().catch((err) => {
    console.error('❌ 失败:', err.message);
    process.exit(1);
  });
}
