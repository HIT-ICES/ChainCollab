const axios = require('axios');
const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
require('dotenv').config({ path: path.join(ROOT_DIR, '.env') });

const CHAINLINK_URL = process.env.CHAINLINK_URL || 'http://localhost:6688';
const CHAINLINK_EMAIL = process.env.CHAINLINK_EMAIL || 'admin@chain.link';
const CHAINLINK_PASSWORD = process.env.CHAINLINK_PASSWORD || 'change-me-strong';

const JOB_SPEC_PATH = path.resolve(__dirname, 'job-spec-dmn-event.toml');

const API_ENDPOINTS = {
  LOGIN: '/sessions',
  JOBS: '/v2/jobs',
};

const nodes = [
  { name: 'chainlink1', port: 6688 },
  { name: 'chainlink2', port: 6689 },
  { name: 'chainlink3', port: 6691 },
  { name: 'chainlink4', port: 6692 },
];

const DMN_SERVICE_MAP = {
  chainlink1: 'http://dmn-node1:8080',
  chainlink2: 'http://dmn-node2:8080',
  chainlink3: 'http://dmn-node3:8080',
  chainlink4: 'http://dmn-node4:8080',
};

class ChainlinkJobManager {
  constructor(chainlinkUrl) {
    this.authToken = null;
    this.chainlinkUrl = chainlinkUrl;
  }

  async login() {
    try {
      console.log('🔐 正在登录 Chainlink 节点...');
      console.log('📍 节点地址:', this.chainlinkUrl);

      const response = await axios.post(`${this.chainlinkUrl}${API_ENDPOINTS.LOGIN}`, {
        email: CHAINLINK_EMAIL,
        password: CHAINLINK_PASSWORD,
      });

      if (response.headers['set-cookie']) {
        this.authToken = response.headers['set-cookie'].join('; ');
        console.log('✅ 登录成功');
      } else {
        throw new Error('未获取到会话 Cookie');
      }
    } catch (error) {
      console.error('❌ 登录失败:', error.message);
      if (error.response) {
        console.error('响应状态:', error.response.status);
        console.error('响应数据:', error.response.data);
      }
      throw error;
    }
  }

  async createJob(jobSpec) {
    try {
      console.log('📝 正在创建 DMN directrequest 缓存 Job...');

      const response = await axios.post(
        `${this.chainlinkUrl}${API_ENDPOINTS.JOBS}`,
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
        console.log('');
        console.log('📋 Job 信息:');
        console.log('   Job ID:', response.data.data.id);
        console.log('   外部 Job ID:', response.data.data.attributes.externalJobID);
        console.log('   名称:', response.data.data.attributes.name);
        console.log('   类型:', response.data.data.type);
        console.log('   状态:', response.data.data.attributes.status);
        return response.data.data;
      }
      throw new Error(`请求失败，状态码: ${response.status}`);
    } catch (error) {
      console.error('❌ Job 创建失败:', error.message);
      if (error.response) {
        console.error('响应状态:', error.response.status);
        console.error('响应数据:', error.response.data);
      }
      throw error;
    }
  }
}

function resolveOperatorAddress() {
  const deploymentPath = path.join(ROOT_DIR, 'deployment', 'chainlink-deployment.json');
  if (!fs.existsSync(deploymentPath)) {
    console.error('❌ 找不到 deployment/chainlink-deployment.json，请先部署 Chainlink 基础设施');
    process.exit(1);
  }
  const deployment = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
  if (!deployment.operator) {
    console.error('❌ chainlink-deployment.json 缺少 operator 地址');
    process.exit(1);
  }
  try {
    const ethers = require('ethers');
    return ethers.getAddress(deployment.operator);
  } catch (error) {
    console.error('❌ operator 地址不是有效的 EIP55 格式:', deployment.operator);
    process.exit(1);
  }
}

async function main() {
  try {
    console.log('🎯 DMN directrequest 缓存 Job 创建工具');
    console.log('='.repeat(50));
    console.log('');

    const operatorAddress = resolveOperatorAddress();
    const deploymentPath = path.join(ROOT_DIR, 'deployment', 'chainlink-deployment.json');
    let externalJobId =
      process.env.EXTERNAL_JOB_ID || process.argv[2] || null;

    const jobIds = {};
    for (const node of nodes) {
      console.log(`\n📄 正在为 ${node.name} 读取 Job 配置文件...`);
      let jobSpecContent = fs.readFileSync(JOB_SPEC_PATH, 'utf8');
      jobSpecContent = jobSpecContent.replace('<YOUR_OPERATOR_CONTRACT_ADDRESS>', operatorAddress);
      if (externalJobId) {
        jobSpecContent = jobSpecContent.replace('<DMN_DIRECTREQUEST_EXTERNAL_JOB_ID>', externalJobId);
      } else {
        jobSpecContent = jobSpecContent.replace(/^externalJobID\s*=.*\n/m, '');
      }
      const dmnUrl = DMN_SERVICE_MAP[node.name];
      if (!dmnUrl) {
        throw new Error(`未找到 ${node.name} 的 DMN 服务地址`);
      }
      jobSpecContent = jobSpecContent.replace(/<DMN_CACHE_URL>/g, dmnUrl);
      jobSpecContent = jobSpecContent.replace(/\\"/g, '"');

      console.log(`\n${node.name} Job Spec:`);
      console.log(jobSpecContent);

      const jobManager = new ChainlinkJobManager(`http://localhost:${node.port}`);
      await jobManager.login();
      const jobData = await jobManager.createJob(jobSpecContent);
      if (!externalJobId) {
        externalJobId = jobData.attributes.externalJobID;
        console.log(`✅ 使用第一个节点生成的 externalJobID: ${externalJobId}`);
      }
      jobIds[node.name] = jobData.attributes.externalJobID;
    }

    if (fs.existsSync(deploymentPath)) {
      const deploymentData = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
      if (!deploymentData.dmnJobIds) {
        deploymentData.dmnJobIds = {};
      }
      Object.assign(deploymentData.dmnJobIds, jobIds);
      deploymentData.dmnJobId = jobIds.chainlink1 || deploymentData.dmnJobId;
      fs.writeFileSync(deploymentPath, JSON.stringify(deploymentData, null, 2));
      console.log('✅ 已写入 dmnJobIds/dmnJobId 到 deployment/chainlink-deployment.json');
    }

    console.log('');
    console.log('🎉 DMN directrequest 缓存 Job 创建成功！');
  } catch (error) {
    console.error('');
    console.error('❌ 操作失败:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = ChainlinkJobManager;
