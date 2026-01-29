const axios = require('axios');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
require('dotenv').config({ path: path.join(ROOT_DIR, '.env') });

const CHAINLINK_URL = process.env.CHAINLINK_URL || 'http://localhost:6688';
const CHAINLINK_EMAIL = process.env.CHAINLINK_EMAIL || 'admin@chain.link';
const CHAINLINK_PASSWORD = process.env.CHAINLINK_PASSWORD || 'change-me-strong';

const API_ENDPOINTS = {
  LOGIN: '/sessions',
  JOBS: '/v2/jobs',
};

class ChainlinkJobManager {
  constructor() {
    this.authToken = null;
  }

  async login() {
    try {
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
    } catch (error) {
      console.error('❌ 登录失败:', error.message);
      if (error.response) {
        console.error('响应状态:', error.response.status);
        console.error('响应数据:', error.response.data);
      }
      throw error;
    }
  }

  async deleteJob(jobId) {
    try {
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
    } catch (error) {
      console.error('❌ Job 删除失败:', error.message);
      if (error.response) {
        console.error('响应状态:', error.response.status);
        console.error('响应数据:', error.response.data);
      }
      return false;
    }
  }

  async listJobs() {
    try {
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
    } catch (error) {
      console.error('❌ 获取 Job 列表失败:', error.message);
      if (error.response) {
        console.error('响应状态:', error.response.status);
        console.error('响应数据:', error.response.data);
      }
      throw error;
    }
  }
}

async function main() {
  try {
    console.log('🎯 DMN 事件监听 Job 删除工具');
    console.log('='.repeat(50));
    console.log('');

    const jobIdOrExternal = process.argv[2];
    if (!jobIdOrExternal) {
      console.error('❌ 未提供 Job ID，请传入内部 ID 或外部 ID');
      console.log('用法: node features/04-dmn-ocr/delete-dmn-event-job.js <jobInternalId|externalJobId>');
      process.exit(1);
    }

    const jobManager = new ChainlinkJobManager();
    await jobManager.login();

    let jobId = jobIdOrExternal;
    if (jobIdOrExternal.includes('-')) {
      const jobs = await jobManager.listJobs();
      const found = jobs.find((job) => job?.attributes?.externalJobID === jobIdOrExternal);
      if (!found) {
        console.error('❌ 未找到对应外部 ID 的 Job:', jobIdOrExternal);
        process.exit(1);
      }
      jobId = found.id;
      console.log('✅ 已解析外部 ID 对应的内部 ID:', jobId);
    }

    const deleted = await jobManager.deleteJob(jobId);
    if (!deleted) {
      process.exit(1);
    }

    console.log('');
    console.log('🎉 DMN 事件监听 Job 删除成功！');
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
