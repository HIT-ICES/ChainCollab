const fs = require('fs');
const path = require('path');

function resolveChainlinkRoot() {
  const candidates = [];
  if (process.env.CHAINLINK_ROOT) {
    candidates.push(path.resolve(process.env.CHAINLINK_ROOT));
  }
  candidates.push(path.resolve(__dirname, '..', 'CHAINLINK'));
  candidates.push(path.resolve(__dirname, '..', '..'));

  for (const candidate of candidates) {
    if (fs.existsSync(path.join(candidate, 'deployment')) && fs.existsSync(path.join(candidate, 'package.json'))) {
      return candidate;
    }
  }
  return candidates[0];
}

const ROOT_DIR = resolveChainlinkRoot();
const DEPLOYMENT_DIR = path.resolve(
  process.env.CHAINCOLLAB_RUNTIME_DEPLOYMENT_DIR || path.join(ROOT_DIR, 'deployment')
);
function requireFromChainlink(modName) {
  try {
    return require(modName);
  } catch (_) {
    return require(path.join(ROOT_DIR, 'node_modules', modName));
  }
}

const axios = requireFromChainlink('axios');
requireFromChainlink('dotenv').config({ path: path.join(ROOT_DIR, '.env') });

const CHAINLINK_URL = process.env.CHAINLINK_URL || 'http://localhost:6688';
const CHAINLINK_EMAIL = process.env.CHAINLINK_EMAIL || 'admin@chain.link';
const CHAINLINK_PASSWORD = process.env.CHAINLINK_PASSWORD || 'change-me-strong';
const TASK_KIND =
  String(process.env.CHAINLINK_TASK_KIND || 'dmn').toLowerCase() === 'datasource'
    ? 'datasource'
    : 'dmn';
const JOB_SPEC_PATHS = {
  dmn: path.resolve(__dirname, 'job-spec-dmn-event.toml'),
  datasource: path.resolve(__dirname, 'job-spec-datasource-event.toml'),
};

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
  chainlink1: 'http://cdmn-node1:5000',
  chainlink2: 'http://cdmn-node2:5000',
  chainlink3: 'http://cdmn-node3:5000',
  chainlink4: 'http://cdmn-node4:5000',
};

function getJobMeta(taskKind) {
  if (taskKind === 'datasource') {
    return {
      title: 'Datasource directrequest 缓存 Job 创建工具',
      idsKey: 'datasourceJobIds',
      idKey: 'datasourceJobId',
      successText: 'Datasource directrequest 缓存 Job 创建成功',
    };
  }
  return {
    title: 'DMN directrequest 缓存 Job 创建工具',
    idsKey: 'dmnJobIds',
    idKey: 'dmnJobId',
    successText: 'DMN directrequest 缓存 Job 创建成功',
  };
}

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
      console.log('📝 正在创建 directrequest 缓存 Job...');

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

  async listJobs() {
    const response = await axios.get(`${this.chainlinkUrl}${API_ENDPOINTS.JOBS}`, {
      headers: {
        Cookie: this.authToken,
      },
    });
    return response.data?.data || [];
  }

  async deleteJob(jobId) {
    await axios.delete(`${this.chainlinkUrl}${API_ENDPOINTS.JOBS}/${jobId}`, {
      headers: {
        Cookie: this.authToken,
      },
    });
  }
}

function extractJobName(jobSpec) {
  const m = jobSpec.match(/^\s*name\s*=\s*"([^"]+)"/m);
  return m ? m[1] : null;
}

function resolveOperatorAddress() {
  const deploymentPath = path.join(DEPLOYMENT_DIR, 'chainlink-deployment.json');
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
    const ethers = requireFromChainlink('ethers');
    return ethers.getAddress(deployment.operator);
  } catch (error) {
    console.error('❌ operator 地址不是有效的 EIP55 格式:', deployment.operator);
    process.exit(1);
  }
}

function resolveDmnRequestContract() {
  const deploymentPath = path.join(DEPLOYMENT_DIR, 'deployment.json');
  if (!fs.existsSync(deploymentPath)) {
    return null;
  }
  const deployment = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
  return deployment.contractAddress || null;
}

async function main() {
  try {
    const jobMeta = getJobMeta(TASK_KIND);
    const jobSpecPath = JOB_SPEC_PATHS[TASK_KIND] || JOB_SPEC_PATHS.dmn;
    if (!fs.existsSync(jobSpecPath)) {
      console.error(`❌ 找不到 Job 模板: ${jobSpecPath}`);
      process.exit(1);
    }

    console.log(`🎯 ${jobMeta.title}`);
    console.log('='.repeat(50));
    console.log('');

    const operatorAddress = resolveOperatorAddress();
    let contractAddress =
      process.env.DMN_REQUEST_CONTRACT_ADDRESS || resolveDmnRequestContract();
    const allowEmptyContract = process.env.ALLOW_EMPTY_DMN_REQUEST_CONTRACT === '1';
    if (!contractAddress) {
      if (!allowEmptyContract) {
        console.error('❌ 缺少 DMN 请求合约地址：deployment/deployment.json 或 DMN_REQUEST_CONTRACT_ADDRESS');
        console.error('   或设置 ALLOW_EMPTY_DMN_REQUEST_CONTRACT=1 先创建 Job，部署后再重建');
        process.exit(1);
      }
      contractAddress = '0x0000000000000000000000000000000000000000';
      console.warn('⚠️  使用占位合约地址 0x0 创建 Job，部署后请重建 Job 以更新合约地址');
    }
    const deploymentPath = path.join(DEPLOYMENT_DIR, 'chainlink-deployment.json');
    let externalJobId =
      process.env.EXTERNAL_JOB_ID || process.argv[2] || null;

    const jobIds = {};
    const recreateOnRun = process.env.RECREATE_JOB === '1';
    for (const node of nodes) {
      console.log(`\n📄 正在为 ${node.name} 读取 Job 配置文件...`);
      let jobSpecContent = fs.readFileSync(jobSpecPath, 'utf8');
      jobSpecContent = jobSpecContent.replace('<YOUR_OPERATOR_CONTRACT_ADDRESS>', operatorAddress);
      if (externalJobId) {
        jobSpecContent = jobSpecContent.replace(
          /<DMN_DIRECTREQUEST_EXTERNAL_JOB_ID>|<DIRECTREQUEST_EXTERNAL_JOB_ID>/g,
          externalJobId
        );
      } else {
        jobSpecContent = jobSpecContent.replace(/^externalJobID\s*=.*\n/m, '');
      }
      if (TASK_KIND === 'dmn') {
        const dmnUrl = DMN_SERVICE_MAP[node.name];
        if (!dmnUrl) {
          throw new Error(`未找到 ${node.name} 的 DMN 服务地址`);
        }
        jobSpecContent = jobSpecContent.replace(/<DMN_CACHE_URL>/g, dmnUrl);
      } else {
        const dataSourceUrlExpr = process.env.DATA_SOURCE_URL || '$(decode_cbor.url)';
        const dataSourceMethod = (process.env.DATA_SOURCE_HTTP_METHOD || 'GET').toUpperCase();
        jobSpecContent = jobSpecContent.replace(/<DATA_SOURCE_URL_EXPR>/g, dataSourceUrlExpr);
        jobSpecContent = jobSpecContent.replace(/<DATA_SOURCE_HTTP_METHOD>/g, dataSourceMethod);
      }
      jobSpecContent = jobSpecContent.replace(/<DMN_REQUEST_CONTRACT_ADDRESS>/g, contractAddress);
      jobSpecContent = jobSpecContent.replace(/\\"/g, '"');
      const jobName = extractJobName(jobSpecContent);

      console.log(`\n${node.name} Job Spec:`);
      console.log(jobSpecContent);

      const jobManager = new ChainlinkJobManager(`http://localhost:${node.port}`);
      await jobManager.login();

      const jobs = await jobManager.listJobs();
      const matched = jobs.filter((job) => {
        const attrs = job.attributes || {};
        const byExternalId = externalJobId && attrs.externalJobID === externalJobId;
        const byName = jobName && attrs.name === jobName;
        return Boolean(byExternalId || byName);
      });

      if (matched.length > 0 && !recreateOnRun) {
        const preferred =
          matched.find((job) => (job.attributes || {}).externalJobID === externalJobId) ||
          matched[0];
        const reusedExternalId = preferred?.attributes?.externalJobID || externalJobId;
        externalJobId = reusedExternalId || externalJobId;
        jobIds[node.name] = reusedExternalId || '';
        console.log(
          `♻️  复用 ${node.name} 已有 Job: ${preferred.id} (${preferred.attributes?.name || 'unnamed'})`
        );
        console.log(`   externalJobID: ${reusedExternalId || '(empty)'}`);
        continue;
      }

      if (matched.length > 0 && recreateOnRun) {
        console.log(`🧹 清理 ${node.name} 上冲突 Job（按 externalJobID/name 匹配）: ${matched.length} 个`);
        for (const job of matched) {
          console.log(`   - 删除 Job: ${job.id} (${job.attributes?.name || 'unnamed'})`);
          await jobManager.deleteJob(job.id);
        }
      }
      const jobData = await jobManager.createJob(jobSpecContent);
      if (!externalJobId) {
        externalJobId = jobData.attributes.externalJobID;
        console.log(`✅ 使用第一个节点生成的 externalJobID: ${externalJobId}`);
      }
      jobIds[node.name] = jobData.attributes.externalJobID;
    }

    if (fs.existsSync(deploymentPath)) {
      const deploymentData = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
      if (!deploymentData[jobMeta.idsKey]) {
        deploymentData[jobMeta.idsKey] = {};
      }
      Object.assign(deploymentData[jobMeta.idsKey], jobIds);
      deploymentData[jobMeta.idKey] = jobIds.chainlink1 || deploymentData[jobMeta.idKey];
      fs.writeFileSync(deploymentPath, JSON.stringify(deploymentData, null, 2));
      console.log(`✅ 已写入 ${jobMeta.idsKey}/${jobMeta.idKey} 到 deployment/chainlink-deployment.json`);
    }

    console.log('');
    console.log(`🎉 ${jobMeta.successText}！`);
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
