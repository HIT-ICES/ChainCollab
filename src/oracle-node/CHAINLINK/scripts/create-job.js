const http = require('http');
const fs = require('fs');
const { keccak256 } = require('@ethersproject/keccak256');
const { toUtf8Bytes } = require('@ethersproject/strings');

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

const username = 'admin@chain.link';
const password = 'change-me-strong';
const chainlinkUrl = 'http://localhost:6688';

// 登录获取 session cookie
function login() {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            email: username,
            password: password
        });

        const options = {
            hostname: 'localhost',
            port: 6688,
            path: '/sessions',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        const req = http.request(options, (res) => {
            const cookies = res.headers['set-cookie'];
            if (res.statusCode === 200 && cookies) {
                resolve(cookies.join('; '));
            } else {
                reject(new Error(`Login failed with status ${res.statusCode}`));
            }
        });

        req.on('error', reject);
        req.write(postData);
        req.end();
    });
}

// 创建 Job
function createJob(cookie, jobSpec) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({ toml: jobSpec });

        const options = {
            hostname: 'localhost',
            port: 6688,
            path: '/v2/jobs',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData),
                'Cookie': cookie
            }
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                if (res.statusCode === 200) {
                    resolve(JSON.parse(data));
                } else {
                    reject(new Error(`Failed to create job: ${res.statusCode} - ${data}`));
                }
            });
        });

        req.on('error', reject);
        req.write(postData);
        req.end();
    });
}

async function main() {
    try {
        console.log('正在连接到 Chainlink 节点...');

        // 登录
        console.log('正在登录...');
        const cookie = await login();
        console.log('✅ 登录成功');

        // 检查 chainlink-deployment.json 文件是否存在
        const deploymentDir = 'deployment';
        if (!fs.existsSync(`${deploymentDir}/chainlink-deployment.json`)) {
            console.error('❌ 找不到 chainlink-deployment.json 文件，请先部署 Chainlink 基础设施');
            process.exit(1);
        }

        // 读取 chainlink-deployment.json 文件
        const chainlinkDeployment = JSON.parse(fs.readFileSync(`${deploymentDir}/chainlink-deployment.json`, 'utf8'));
        const operatorAddress = chainlinkDeployment.operator;

        // 读取 Job Spec
        let jobSpec = fs.readFileSync('config/job-spec.toml', 'utf8');

        // 动态替换合约地址，确保是 EIP55 格式
        const checksumAddress = toChecksumAddress(operatorAddress);
        jobSpec = jobSpec.replace(/0x75CD7081c3224a11B2b013fAED8606Acd4cec737/g, checksumAddress);

        console.log('\n读取 Job Spec:');
        console.log(jobSpec);

        // 创建 Job
        console.log('\n正在创建 Job...');
        const result = await createJob(cookie, jobSpec);

        console.log('\n✅ Job 创建成功!');
        console.log('Job ID:', result.data.id);
        console.log('Job External Job ID:', result.data.attributes.externalJobID);

        // 保存 Job ID
        const deployment = JSON.parse(fs.readFileSync(`${deploymentDir}/chainlink-deployment.json`, 'utf8'));
        deployment.jobId = result.data.attributes.externalJobID;
        deployment.jobInternalId = result.data.id;
        fs.writeFileSync(`${deploymentDir}/chainlink-deployment.json`, JSON.stringify(deployment, null, 2));

        console.log('\n========================================');
        console.log('✅ Chainlink 设置完成!');
        console.log('========================================');
        console.log('LINK Token:', deployment.linkToken);
        console.log('Operator:', deployment.operator);
        console.log('Job ID:', deployment.jobId);
        console.log('\n现在你可以使用这些信息重新部署 MyChainlinkRequester 合约');
        console.log(`或者访问 ${chainlinkUrl} 查看 Job 详情`);

    } catch (error) {
        console.error('\n❌ 失败:', error.message);
        process.exit(1);
    }
}

main();
