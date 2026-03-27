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

    async getJobs() {
        try {
            console.log('📋 正在获取 Job 列表...');

            const response = await axios.get(`${CHAINLINK_URL}${API_ENDPOINTS.JOBS}`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Cookie': this.authToken
                }
            });

            if (response.status === 200) {
                console.log('✅ Job 列表获取成功!');
                return response.data.data;
            } else {
                throw new Error(`请求失败，状态码: ${response.status}`);
            }
        } catch (error) {
            console.error('❌ 无法获取 Job 列表:', error.message);
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
        console.log('🎯 获取 Chainlink 节点 Job 列表');
        console.log('='.repeat(50));
        console.log('');

        // 创建 Job 管理器
        const jobManager = new ChainlinkJobManager();

        // 登录
        await jobManager.login();

        // 获取 Job 列表
        const jobs = await jobManager.getJobs();

        if (jobs && jobs.length > 0) {
            console.log('');
            console.log('📊 节点上的 Job 列表:');
            jobs.forEach(job => {
                console.log('');
                console.log(`   ID: ${job.id}`);
                console.log(`   名称: ${job.name}`);
                console.log(`   类型: ${job.type}`);
                console.log(`   状态: ${job.status}`);
                console.log(`   创建时间: ${job.createdAt}`);
            });
        } else {
            console.log('');
            console.log('⚠️  节点上没有找到 Job');
        }

        console.log('');
        console.log('🎉 获取 Job 列表成功！');

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
