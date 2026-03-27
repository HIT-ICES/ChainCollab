#!/usr/bin/env node

const http = require('http');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

const username = 'admin@chain.link';
const password = 'change-me-strong';

// 节点配置
const nodes = [
  { name: 'bootstrap', container: 'chainlink-bootstrap', port: 6687 },
  { name: 'node1', container: 'chainlink-node1', port: 6688 },
  { name: 'node2', container: 'chainlink-node2', port: 6689 },
  { name: 'node3', container: 'chainlink-node3', port: 6691 },
  { name: 'node4', container: 'chainlink-node4', port: 6692 }
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
      },
      timeout: 5000 // 设置 5 秒超时
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
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('Login request timeout'));
    });
    req.write(postData);
    req.end();
  });
}

// 获取 ETH 密钥列表 (使用 GraphQL API)
function getETHKeys(cookie, port) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      operationName: "FetchETHKeys",
      variables: {},
      query: `fragment ETHKeysPayload_ResultsFields on EthKey {
        address
        chain {
          id
          __typename
        }
        createdAt
        ethBalance
        isDisabled
        linkBalance
        __typename
      }

      query FetchETHKeys {
        ethKeys {
          results {
            ...ETHKeysPayload_ResultsFields
            __typename
          }
          __typename
        }
      }
      `
    });

    const options = {
      hostname: 'localhost',
      port: port,
      path: '/query',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': cookie,
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
        'Origin': `http://localhost:${port}`,
        'Referer': `http://localhost:${port}/keys`,
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
      },
      timeout: 5000 // 设置 5 秒超时
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        if (res.statusCode === 200) {
          const result = JSON.parse(data);
          if (result.data && result.data.ethKeys) {
            resolve(result.data.ethKeys.results);
          } else {
            reject(new Error(`GraphQL error: ${JSON.stringify(result.errors || result.data)}`));
          }
        } else {
          reject(new Error(`Failed to get ETH keys: ${res.statusCode} - ${data}`));
        }
      });
    });

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('Get ETH keys request timeout'));
    });
    req.write(postData);
    req.end();
  });
}

// 获取 OCR 密钥列表 (使用 GraphQL API)
function getOCRKeys(cookie, port) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      operationName: "FetchOCRKeyBundles",
      variables: {},
      query: `fragment OCRKeyBundlesPayload_ResultsFields on OCRKeyBundle {
        id
        configPublicKey
        offChainPublicKey
        onChainSigningAddress
        __typename
      }

      query FetchOCRKeyBundles {
        ocrKeyBundles {
          results {
            ...OCRKeyBundlesPayload_ResultsFields
            __typename
          }
          __typename
        }
      }
      `
    });

    const options = {
      hostname: 'localhost',
      port: port,
      path: '/query',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': cookie,
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
        'Origin': `http://localhost:${port}`,
        'Referer': `http://localhost:${port}/keys`,
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
      },
      timeout: 5000 // 设置 5 秒超时

    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        if (res.statusCode === 200) {
          const result = JSON.parse(data);
          if (result.data && result.data.ocrKeyBundles) {
            resolve(result.data.ocrKeyBundles.results);
          } else {
            reject(new Error(`GraphQL error: ${JSON.stringify(result.errors || result.data)}`));
          }
        } else {
          reject(new Error(`Failed to get OCR keys: ${res.statusCode} - ${data}`));
        }
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

// 获取 P2P 密钥列表 (使用 GraphQL API)
function getP2PKeys(cookie, port) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      operationName: "FetchP2PKeys",
      variables: {},
      query: `fragment P2PKeysPayload_ResultsFields on P2PKey {
        id
        peerID
        publicKey
        __typename
      }

      query FetchP2PKeys {
        p2pKeys {
          results {
            ...P2PKeysPayload_ResultsFields
            __typename
          }
          __typename
        }
      }
      `
    });

    const options = {
      hostname: 'localhost',
      port: port,
      path: '/query',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': cookie,
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
        'Origin': `http://localhost:${port}`,
        'Referer': `http://localhost:${port}/keys`,
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
      },
      timeout: 5000 // 设置 5 秒超时

    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        if (res.statusCode === 200) {
          const result = JSON.parse(data);
          if (result.data && result.data.p2pKeys) {
            resolve(result.data.p2pKeys.results);
          } else {
            reject(new Error(`GraphQL error: ${JSON.stringify(result.errors || result.data)}`));
          }
        } else {
          reject(new Error(`Failed to get P2P keys: ${res.statusCode} - ${data}`));
        }
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

// 获取单个节点的信息
async function getNodeInfo(node) {
  console.log(`=== 获取 ${node.name} 信息 ===`);

  try {
    // 登录
    const cookie = await login(node.port);

    let ethAddress = null;
    let ocrKeyBundleId = null;
    let signerAddress = null;
    let ocrOffchainPublicKey = null;
    let ocrConfigPublicKey = null;

    // 如果不是只获取 Bootstrap 节点信息，则获取 ETH 密钥和 OCR 密钥
    if (process.argv[2] !== 'bootstrap') {
      // 获取 ETH 密钥
      const ethKeys = await getETHKeys(cookie, node.port);
      ethAddress = ethKeys.length > 0 ? ethKeys[0].address : null;

      // 获取 OCR 密钥
      const ocrKeys = await getOCRKeys(cookie, node.port);
      ocrKeyBundleId = ocrKeys.length > 0 ? ocrKeys[0].id : null;
      signerAddress = ocrKeys.length > 0 ? ocrKeys[0].onChainSigningAddress : null;
      ocrOffchainPublicKey = ocrKeys.length > 0 ? ocrKeys[0].offChainPublicKey : null;
      ocrConfigPublicKey = ocrKeys.length > 0 ? ocrKeys[0].configPublicKey : null;
    }

    // 获取 P2P 密钥
    const p2pKeys = await getP2PKeys(cookie, node.port);
    const p2pPeerId = p2pKeys.length > 0 ? p2pKeys[0].peerID : null;

    const hostIP = '172.31.61.180';

    const nodeInfo = {
      name: node.name,
      container: node.container,
      port: node.port,
      containerIP: null,
      ethAddress,
      ocrKeyBundleId,
      signerAddress,
      ocrOffchainPublicKey,
      ocrConfigPublicKey,
      p2pPeerId: p2pPeerId ? p2pPeerId.replace('p2p_', '') : null,
      // 构建 P2P 地址 - 优先使用容器 IP，其次使用 hostname
      p2pAddress: p2pPeerId ? `/ip4/${hostIP}/tcp/${node.name === 'bootstrap' ? '6690' :
          node.name === 'node1' ? '6698' :
            node.name === 'node2' ? '6699' :
              node.name === 'node3' ? '6697' :
                '6696'
        }/p2p/${p2pPeerId.replace('p2p_', '')}` : null
    };

    // 如果是只获取 Bootstrap 节点信息，则只显示 P2P 相关信息
    if (process.argv[2] === 'bootstrap') {
      console.log(`P2P Peer ID: ${nodeInfo.p2pPeerId}`);
      console.log(`P2P Address: ${nodeInfo.p2pAddress}`);
    } else {
      console.log(`ETH Address: ${nodeInfo.ethAddress}`);
      console.log(`OCR Key Bundle ID: ${nodeInfo.ocrKeyBundleId}`);
      console.log(`OCR Signer Address: ${nodeInfo.signerAddress}`);
      console.log(`OCR Offchain Public Key: ${nodeInfo.ocrOffchainPublicKey}`);
      console.log(`OCR Config Public Key: ${nodeInfo.ocrConfigPublicKey}`);
      console.log(`P2P Peer ID: ${nodeInfo.p2pPeerId}`);
      console.log(`P2P Address: ${nodeInfo.p2pAddress}`);
    }
    console.log();

    return nodeInfo;

  } catch (error) {
    console.error(`获取 ${node.name} 信息失败:`, error.message);
    return null;
  }
}

async function main() {
  // 支持只获取特定节点的信息
  const targetNode = process.argv[2];

  if (targetNode) {
    console.log(`开始收集 ${targetNode} 节点的信息\n`);
  } else {
    console.log('开始收集所有 Chainlink 节点的信息\n');
  }

  const allNodeInfo = [];

  for (const node of nodes) {
    if (targetNode && node.name !== targetNode) {
      continue;
    }

    const info = await getNodeInfo(node);
    if (info) {
      allNodeInfo.push(info);
    }
  }

  // 检查是否所有节点信息都收集成功
  // 如果只获取特定节点，并且是 bootstrap 节点，则只检查 P2P 密钥
  // 对于所有节点的信息收集，如果是 bootstrap 节点，则不要求 OCR 密钥存在
  const missingInfoNodes = [];

  allNodeInfo.forEach(node => {
    if (targetNode === 'bootstrap') {
      if (!node.p2pPeerId) {
        missingInfoNodes.push(node);
      }
    } else {
      if (node.name === 'bootstrap') {
        if (!node.ethAddress || !node.p2pPeerId) {
          missingInfoNodes.push(node);
        }
      } else {
        if (!node.ethAddress || !node.ocrKeyBundleId || !node.signerAddress || !node.ocrOffchainPublicKey || !node.ocrConfigPublicKey || !node.p2pPeerId) {
          missingInfoNodes.push(node);
        }
      }
    }
  });

  if (missingInfoNodes.length > 0) {
    console.error('⚠️  以下节点信息收集不完整:');
    missingInfoNodes.forEach(node => {
      if (targetNode === 'bootstrap') {
        console.error(`  - ${node.name}: P2P Key 缺失`);
      } else {
        console.error(`  - ${node.name}: ${!node.ethAddress ? 'ETH Address ' : ''}${!node.ocrKeyBundleId ? 'OCR Key ' : ''}${!node.signerAddress ? 'OCR Signer Address ' : ''}${!node.ocrOffchainPublicKey ? 'OCR Offchain Public Key ' : ''}${!node.ocrConfigPublicKey ? 'OCR Config Public Key ' : ''}${!node.p2pPeerId ? 'P2P Key ' : ''}缺失`);
      }
    });

    console.error('\n请确保所有节点已启动并已生成密钥');
    process.exit(1);
  }

  // 保存节点信息
  const deploymentDir = path.join(ROOT_DIR, 'deployment');
  if (!fs.existsSync(deploymentDir)) {
    fs.mkdirSync(deploymentDir);
  }

  const nodeInfoFile = `${deploymentDir}/node-info.json`;
  fs.writeFileSync(nodeInfoFile, JSON.stringify(allNodeInfo, null, 2));

  console.log(`✅ 所有节点信息已保存到 ${nodeInfoFile}`);
  console.log();

  // 显示 OCR 配置信息
  console.log('=== OCR 网络配置信息 ===');
  console.log('1. P2P Bootstrap Peers:');
  allNodeInfo.forEach(node => {
    console.log(`   - ${node.p2pAddress}`);
  });

  // 如果不是只获取 Bootstrap 节点信息，则显示 ETH 地址和 OCR 密钥的配置信息
  if (process.argv[2] !== 'bootstrap') {
    console.log('2. 节点 ETH 地址 (用于 setConfig):');
    allNodeInfo.forEach(node => {
      console.log(`   - ${node.name}: ${node.ethAddress}`);
    });
    console.log();

    console.log('3. 节点 OCR Key Bundle IDs (用于 setConfig):');
    allNodeInfo.forEach(node => {
      console.log(`   - ${node.name}: ${node.ocrKeyBundleId}`);
    });
    console.log();

    console.log('4. 节点 OCR Signer Addresses (用于 setConfig):');
    allNodeInfo.forEach(node => {
      console.log(`   - ${node.name}: ${node.signerAddress}`);
    });
    console.log();

    console.log('5. 节点 OCR Offchain Public Keys:');
    allNodeInfo.forEach(node => {
      console.log(`   - ${node.name}: ${node.ocrOffchainPublicKey}`);
    });
    console.log();

    console.log('6. 节点 OCR Config Public Keys:');
    allNodeInfo.forEach(node => {
      console.log(`   - ${node.name}: ${node.ocrConfigPublicKey}`);
    });
  }
}

main();
