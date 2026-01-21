const http = require('http');
const fs = require('fs');

const username = 'admin@chain.link';
const password = 'change-me-strong';

// 为每个节点创建 OCR Job 的配置
const nodes = [
  { name: 'chainlink-bootstrap', port: 6687, isBootstrap: true },
  { name: 'chainlink1', port: 6688, isBootstrap: false },
  { name: 'chainlink2', port: 6689, isBootstrap: false },
  { name: 'chainlink3', port: 6691, isBootstrap: false },
  { name: 'chainlink4', port: 6692, isBootstrap: false }
];

// 登录获取 session cookie
function login(port) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      email: username,
      password: password
    });

    const options = {
      hostname: 'localhost',
      port: port,
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
function createJob(cookie, port, jobSpec) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({ toml: jobSpec });

    const options = {
      hostname: 'localhost',
      port: port,
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

async function createOCRJobForNode(node) {
  try {
    console.log(`\n正在连接到 Chainlink ${node.name} (端口: ${node.port})...`);

    // 登录
    console.log(`正在登录 ${node.name}...`);
    const cookie = await login(node.port);
    console.log(`✅ ${node.name} 登录成功`);

    // 根据是否是 bootstrap 节点选择不同的 Job Spec
    let jobSpec;
    if (node.isBootstrap) {
      jobSpec = fs.readFileSync('config/job-spec-ocr-bootstrap.toml', 'utf8');
    } else {
      jobSpec = fs.readFileSync('config/job-spec-ocr.toml', 'utf8');
    }

    // 检查 ocr-deployment.json 文件是否存在
    const deploymentDir = 'deployment';
    let ocrContractAddress = '<YOUR_OCR_V1_AGGREGATOR_ADDRESS>';
    if (fs.existsSync(`${deploymentDir}/ocr-deployment.json`)) {
      const ocrDeployment = JSON.parse(fs.readFileSync(`${deploymentDir}/ocr-deployment.json`, 'utf8'));
      // 确保合约地址是 EIP55 格式
      try {
        const ethers = require('ethers');
        ocrContractAddress = ethers.getAddress(ocrDeployment.contractAddress);
      } catch (error) {
        console.error(`❌ 无效的合约地址: ${ocrDeployment.contractAddress}`);
        ocrContractAddress = '<YOUR_OCR_V1_AGGREGATOR_ADDRESS>';
      }
    }

    // 获取节点信息
    let transmitterAddress = '<YOUR_ONCHAIN_TRANSMITTER_ADDRESS>';
    let ocrKeyBundleId = '<YOUR_OCR_KEY_BUNDLE_ID>';
    if (fs.existsSync(`${deploymentDir}/node-info.json`)) {
      const nodeInfo = JSON.parse(fs.readFileSync(`${deploymentDir}/node-info.json`, 'utf8'));
      // 正确匹配节点名称：chainlink-bootstrap → bootstrap，chainlink1 → node1，chainlink2 → node2，chainlink3 → node3
      let lookupName = node.name;
      if (lookupName === 'chainlink-bootstrap') {
        lookupName = 'bootstrap';
      } else if (lookupName.startsWith('chainlink')) {
        lookupName = 'node' + lookupName.slice('chainlink'.length);
      }
      const currentNode = nodeInfo.find(n => n.name === lookupName);
      if (currentNode) {
        transmitterAddress = currentNode.ethAddress;
        ocrKeyBundleId = currentNode.ocrKeyBundleId;
      }
    }

    // 替换占位符
    jobSpec = jobSpec.replace(/<YOUR_OCR_V1_AGGREGATOR_ADDRESS>/g, ocrContractAddress);
    jobSpec = jobSpec.replace(/<YOUR_OFFCHAIN_AGGREGATOR_ADDRESS>/g, ocrContractAddress);
    jobSpec = jobSpec.replace(/<YOUR_ONCHAIN_TRANSMITTER_ADDRESS>/g, transmitterAddress);
    jobSpec = jobSpec.replace(/<YOUR_OCR_KEY_BUNDLE_ID>/g, ocrKeyBundleId);

    // 对于非 bootstrap 节点，替换 p2pBootstrapPeers 配置
    if (!node.isBootstrap) {
      if (fs.existsSync(`${deploymentDir}/node-info.json`)) {
        const nodeInfo = JSON.parse(fs.readFileSync(`${deploymentDir}/node-info.json`, 'utf8'));
        const bootstrapNode = nodeInfo.find(n => n.name === 'bootstrap');
        if (bootstrapNode) {
          // 使用节点信息中的实际 p2p 地址
          jobSpec = jobSpec.replace(/p2pBootstrapPeers\s*=\s*\[[\s\S]*?\]/g, `p2pBootstrapPeers = ["${bootstrapNode.p2pAddress}"]`);
        }
      }
    } else {
      // 对于 bootstrap 节点，确保 p2pBootstrapPeers 是空数组
      jobSpec = jobSpec.replace(/p2pBootstrapPeers\s*=\s*\[[\s\S]*?\]/g, 'p2pBootstrapPeers = []');
    }

    console.log(`\n${node.name} Job Spec:`);
    console.log(jobSpec);

    // 创建 Job
    console.log(`\n正在为 ${node.name} 创建 OCR Job...`);
    const result = await createJob(cookie, node.port, jobSpec);

    console.log(`\n✅ ${node.name} OCR Job 创建成功!`);
    console.log('Job ID:', result.data.id);
    console.log('Job External Job ID:', result.data.attributes.externalJobID);

    return result.data.attributes.externalJobID;

  } catch (error) {
    console.error(`\n❌ ${node.name} 创建 OCR Job 失败:`, error.message);
    return null;
  }
}

async function main() {
  console.log('========================================');
  console.log('开始为所有 Chainlink 节点创建 OCR Job');
  console.log('========================================');

  const jobIds = {};

  for (const node of nodes) {
    const jobId = await createOCRJobForNode(node);
    if (jobId) {
      jobIds[node.name] = jobId;
    }
  }

  console.log('\n========================================');
  console.log('OCR Job 创建结果:');
  console.log('========================================');

  for (const node in jobIds) {
    console.log(`${node}: ${jobIds[node]}`);
  }

  // 保存 OCR Job IDs
  const deploymentDir = 'deployment';
  if (!fs.existsSync(deploymentDir)) {
    fs.mkdirSync(deploymentDir);
  }

  let deploymentData = {};
  const deploymentFile = `${deploymentDir}/chainlink-deployment.json`;
  if (fs.existsSync(deploymentFile)) {
    deploymentData = JSON.parse(fs.readFileSync(deploymentFile, 'utf8'));
  }

  deploymentData.ocrJobIds = jobIds;
  fs.writeFileSync(deploymentFile, JSON.stringify(deploymentData, null, 2));

  console.log(`\nOCR Job 信息已保存到 ${deploymentFile}`);

  if (Object.keys(jobIds).length === nodes.length) {
    console.log('\n✅ 所有节点的 OCR Job 创建成功!');
  } else {
    console.log('\n⚠️  部分节点的 OCR Job 创建失败，请检查日志');
  }
}

main();
