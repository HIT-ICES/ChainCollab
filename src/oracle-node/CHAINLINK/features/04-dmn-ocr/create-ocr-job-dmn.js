const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

const username = 'admin@chain.link';
const password = 'change-me-strong';

const nodes = [
  { name: 'chainlink-bootstrap', port: 6687, isBootstrap: true },
  { name: 'chainlink1', port: 6688, isBootstrap: false },
  { name: 'chainlink2', port: 6689, isBootstrap: false },
  { name: 'chainlink3', port: 6691, isBootstrap: false },
  { name: 'chainlink4', port: 6692, isBootstrap: false },
];

const DMN_SERVICE_MAP = {
  chainlink1: 'http://dmn-node1:8080',
  chainlink2: 'http://dmn-node2:8080',
  chainlink3: 'http://dmn-node3:8080',
  chainlink4: 'http://dmn-node4:8080',
};

function login(port) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({ email: username, password });
    const options = {
      hostname: 'localhost',
      port,
      path: '/sessions',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
      },
    };

    const req = http.request(options, (res) => {
      const cookies = res.headers['set-cookie'];
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        if (res.statusCode === 200 && cookies) {
          resolve(cookies.join('; '));
        } else {
          reject(new Error(`Login failed with status ${res.statusCode} - ${data}`));
        }
      });
      res.on('error', reject);
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

function createJob(cookie, port, jobSpec) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({ toml: jobSpec });
    const options = {
      hostname: 'localhost',
      port,
      path: '/v2/jobs',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
        Cookie: cookie,
      },
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
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
    const cookie = await login(node.port);
    console.log(`✅ ${node.name} 登录成功`);

    let jobSpec;
    if (node.isBootstrap) {
      jobSpec = fs.readFileSync(
        path.join(__dirname, '..', '03-ocr-multinode', 'job-spec-ocr-bootstrap.toml'),
        'utf8'
      );
    } else {
      jobSpec = fs.readFileSync(path.join(__dirname, 'job-spec-ocr-dmn.toml'), 'utf8');
    }

    const deploymentDir = path.join(ROOT_DIR, 'deployment');
    let ocrContractAddress = '<YOUR_OCR_V1_AGGREGATOR_ADDRESS>';
    if (fs.existsSync(path.join(deploymentDir, 'ocr-deployment.json'))) {
      const ocrDeployment = JSON.parse(
        fs.readFileSync(path.join(deploymentDir, 'ocr-deployment.json'), 'utf8')
      );
      try {
        const ethers = require('ethers');
        ocrContractAddress = ethers.getAddress(ocrDeployment.contractAddress);
      } catch (error) {
        console.error(`❌ 无效的合约地址: ${ocrDeployment.contractAddress}`);
        ocrContractAddress = '<YOUR_OCR_V1_AGGREGATOR_ADDRESS>';
      }
    }

    let transmitterAddress = '<YOUR_ONCHAIN_TRANSMITTER_ADDRESS>';
    let ocrKeyBundleId = '<YOUR_OCR_KEY_BUNDLE_ID>';
    if (fs.existsSync(path.join(deploymentDir, 'node-info.json'))) {
      const nodeInfo = JSON.parse(fs.readFileSync(path.join(deploymentDir, 'node-info.json'), 'utf8'));
      let lookupName = node.name;
      if (lookupName === 'chainlink-bootstrap') {
        lookupName = 'bootstrap';
      } else if (lookupName.startsWith('chainlink')) {
        lookupName = 'node' + lookupName.slice('chainlink'.length);
      }
      const currentNode = nodeInfo.find((n) => n.name === lookupName);
      if (currentNode) {
        transmitterAddress = currentNode.ethAddress;
        ocrKeyBundleId = currentNode.ocrKeyBundleId;
      }
    }

    jobSpec = jobSpec.replace(/<YOUR_OCR_V1_AGGREGATOR_ADDRESS>/g, ocrContractAddress);
    jobSpec = jobSpec.replace(/<YOUR_OFFCHAIN_AGGREGATOR_ADDRESS>/g, ocrContractAddress);
    jobSpec = jobSpec.replace(/<YOUR_ONCHAIN_TRANSMITTER_ADDRESS>/g, transmitterAddress);
    jobSpec = jobSpec.replace(/<YOUR_OCR_KEY_BUNDLE_ID>/g, ocrKeyBundleId);

    if (!node.isBootstrap) {
      const dmnUrl = DMN_SERVICE_MAP[node.name];
      if (!dmnUrl) {
        throw new Error(`未找到 ${node.name} 的 DMN 服务地址`);
      }
      jobSpec = jobSpec.replace(/<DMN_CACHE_URL>/g, dmnUrl);
    }

    if (!node.isBootstrap) {
      if (fs.existsSync(path.join(deploymentDir, 'node-info.json'))) {
        const nodeInfo = JSON.parse(fs.readFileSync(path.join(deploymentDir, 'node-info.json'), 'utf8'));
        const bootstrapNode = nodeInfo.find((n) => n.name === 'bootstrap');
        if (bootstrapNode) {
          jobSpec = jobSpec.replace(
            /p2pBootstrapPeers\s*=\s*\[[\s\S]*?\]/g,
            `p2pBootstrapPeers = ["${bootstrapNode.p2pAddress}"]`
          );
        }
      }
    } else {
      jobSpec = jobSpec.replace(/p2pBootstrapPeers\s*=\s*\[[\s\S]*?\]/g, 'p2pBootstrapPeers = []');
    }

    console.log(`\n${node.name} Job Spec:`);
    console.log(jobSpec);

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
  console.log('开始为所有 Chainlink 节点创建 OCR Job (DMN 观测)');
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
}

if (require.main === module) {
  main();
}
