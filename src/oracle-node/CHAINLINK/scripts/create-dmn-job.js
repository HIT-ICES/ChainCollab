const axios = require('axios');
const fs = require('fs');
const path = require('path');
const { keccak256 } = require('@ethersproject/keccak256');
const { toUtf8Bytes } = require('@ethersproject/strings');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

// Chainlink 节点配置
const CHAINLINK_URL = process.env.CHAINLINK_URL || 'http://localhost:6688';
const CHAINLINK_EMAIL = process.env.CHAINLINK_EMAIL || 'admin@chain.link';
const CHAINLINK_PASSWORD = process.env.CHAINLINK_PASSWORD || 'change-me-strong';

// Job 配置文件路径
const JOB_SPEC_PATH = path.resolve(__dirname, '../config/job-spec-dmn-java.toml');

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

    async createJob(jobSpec) {
        try {
            console.log('📝 正在创建 DMN Decision Engine Job...');

            const response = await axios.post(`${CHAINLINK_URL}${API_ENDPOINTS.JOBS}`,
                { toml: jobSpec }, {
                headers: {
                    'Content-Type': 'application/json',
                    'Cookie': this.authToken
                }
            });

            if (response.status === 200 && response.data) {
                console.log('✅ Job 创建成功!');
                console.log('');
                console.log('📋 Job 信息:');
                console.log('   Job ID:', response.data.data.id);
                console.log('   外部 Job ID:', response.data.data.attributes.externalJobID);
                console.log('   名称:', response.data.data.attributes.name);
                console.log('   类型:', response.data.data.type);
                console.log('   状态:', response.data.data.attributes.status);
                console.log('');
                console.log('🚀 现在您可以使用此 Job ID 来配置合约');
                return response.data.data;
            } else {
                throw new Error(`请求失败，状态码: ${response.status}`);
            }
        } catch (error) {
            console.error('❌ Job 创建失败:', error.message);
            if (error.response) {
                console.error('响应状态:', error.response.status);
                console.error('响应数据:', error.response.data);
            }
            throw error;
        }
    }

    async verifyJob(jobId) {
        try {
            console.log('🔍 正在验证 Job...');

            const response = await axios.get(`${CHAINLINK_URL}${API_ENDPOINTS.JOBS}/${jobId}`, {
                headers: {
                    'Cookie': this.authToken
                }
            });

            if (response.status === 200) {
                console.log('✅ Job 验证成功');
                console.log('   名称:', response.data.data.attributes.name);
                console.log('   状态:', response.data.data.attributes.status);
                console.log('   类型:', response.data.data.type);
                console.log('   外部 Job ID:', response.data.data.attributes.externalJobID);
                return response.data.data;
            } else {
                throw new Error(`验证失败，状态码: ${response.status}`);
            }
        } catch (error) {
            console.error('❌ Job 验证失败:', error.message);
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
        console.log('🎯 DMN Job 创建工具');
        console.log('='.repeat(50));
        console.log('');

        // 读取 job spec 文件
        console.log('📄 正在读取 Job 配置文件...');
        let jobSpecContent = fs.readFileSync(JOB_SPEC_PATH, 'utf8');

        // 检查 chainlink-deployment.json 文件是否存在
        const deploymentDir = 'deployment';
        if (!fs.existsSync(`${deploymentDir}/chainlink-deployment.json`)) {
            console.error('❌ 找不到 chainlink-deployment.json 文件，请先部署 Chainlink 基础设施');
            process.exit(1);
        }

        // 读取 chainlink-deployment.json 文件
        const chainlinkDeployment = JSON.parse(fs.readFileSync(`${deploymentDir}/chainlink-deployment.json`, 'utf8'));
        const operatorAddress = chainlinkDeployment.operator;

        // EIP55 地址格式化函数
        function toChecksumAddress(address) {
            address = address.toLowerCase().replace('0x', '');
            const hash = keccak256(toUtf8Bytes(address)).slice(2);
            let result = '0x';
            for (let i = 0; i < address.length; i++) {
                result += parseInt(hash[i], 16) >= 8 ?
                          address[i].toUpperCase() :
                          address[i].toLowerCase();
            }
            return result;
        }

        // 动态替换合约地址，确保是 EIP55 格式
        const checksumAddress = toChecksumAddress(operatorAddress);
        jobSpecContent = jobSpecContent.replace(/0x5430d622657AB294D93c836D4C2fb5dB5F92BDC2/g, checksumAddress);

        // 处理 JSON 字符串中的转义引号
        jobSpecContent = jobSpecContent.replace(/\\"/g, '"');

        console.log('\n读取 Job Spec:');
        console.log(jobSpecContent);

        // 创建 Job 管理器
        const jobManager = new ChainlinkJobManager();

        // 登录
        await jobManager.login();

        // 创建 Job
        const jobData = await jobManager.createJob(jobSpecContent);

        // 验证 Job
        await jobManager.verifyJob(jobData.id);

        console.log('');
        console.log('🎉 DMN Decision Engine Job 创建成功！');
        console.log('');
        console.log('📋 下一步操作:');
        console.log('1. 确保 DMN 服务器正在运行:');
        console.log('   cd oracle-node/CHAINLINK/scripts');
        console.log('   ./start-dmn-server.sh');
        console.log('');
        console.log('2. 更新部署信息:');
        console.log('   将 Job ID', jobData.attributes.externalJobID, '保存到 deployment/chainlink-deployment.json');
        console.log('');
        console.log('3. 测试 Job:');
        console.log('   node scripts/test-dmn-oracle.js');
        console.log('');

        // 更新部署信息
        const deploymentPath = path.resolve(__dirname, '../deployment/chainlink-deployment.json');
        if (fs.existsSync(deploymentPath)) {
            const deploymentData = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
            deploymentData.dmnJobId = jobData.attributes.externalJobID;
            deploymentData.dmnJobInternalId = jobData.id;
            fs.writeFileSync(deploymentPath, JSON.stringify(deploymentData, null, 2));
            console.log('✅ 部署信息已更新');
        }

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
