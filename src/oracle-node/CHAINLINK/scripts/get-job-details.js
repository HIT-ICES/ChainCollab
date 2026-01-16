const axios = require('axios');
const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

// Chainlink 节点配置
const CHAINLINK_URL = process.env.CHAINLINK_URL || 'http://localhost:6688';
const CHAINLINK_EMAIL = process.env.CHAINLINK_EMAIL || 'admin@chain.link';
const CHAINLINK_PASSWORD = process.env.CHAINLINK_PASSWORD || 'change-me-strong';

// API 端点
const API_ENDPOINTS = {
    LOGIN: '/sessions',
    JOBS: '/v2/jobs'
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
                password: CHAINLINK_PASSWORD
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

    async getJobDetails(jobId) {
        try {
            console.log(`📋 正在获取 Job ${jobId} 的详细信息...`);

            const response = await axios.get(`${CHAINLINK_URL}${API_ENDPOINTS.JOBS}/${jobId}`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Cookie': this.authToken
                }
            });

            if (response.status === 200) {
                console.log('✅ Job 详细信息获取成功!');
                return response.data;
            } else {
                throw new Error(`请求失败，状态码: ${response.status}`);
            }
        } catch (error) {
            console.error('❌ 无法获取 Job 详细信息:', error.message);
            if (error.response) {
                console.error('响应状态:', error.response.status);
                console.error('响应数据:', error.response.data);
            }
            return null;
        }
    }
}

async function main() {
    try {
        console.log('🎯 获取 Chainlink 节点 Job 详细信息');
        console.log('='.repeat(50));
        console.log('');

        // 从 chainlink-deployment.json 文件中读取 Job ID
        const deploymentPath = path.resolve(__dirname, '../deployment/chainlink-deployment.json');
        if (!fs.existsSync(deploymentPath)) {
            console.error('❌ 找不到 chainlink-deployment.json 文件，请先部署 Chainlink 基础设施');
            process.exit(1);
        }

        const chainlinkDeployment = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
        const jobId = chainlinkDeployment.dmnJobInternalId;
        if (!jobId) {
            console.error('❌ 未找到 DMN Job ID，请先创建 DMN Job');
            console.log('使用方法: node scripts/create-dmn-job.js');
            process.exit(1);
        }

        // 创建 Job 管理器
        const jobManager = new ChainlinkJobManager();

        // 登录
        await jobManager.login();

        // 获取 Job 详细信息
        const job = await jobManager.getJobDetails(jobId);

        if (job) {
            console.log('');
            console.log('📊 Job 详细信息:');
            console.log('');
            console.log('   原始数据:');
            console.log(JSON.stringify(job, null, 2));
        } else {
            console.log('');
            console.log('⚠️  未找到 Job');
        }

        console.log('');
        console.log('🎉 获取 Job 详细信息成功！');

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
