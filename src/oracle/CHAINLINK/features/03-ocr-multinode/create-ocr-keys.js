const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

const username = 'admin@chain.link';
const password = 'change-me-strong';

// 节点配置
const nodes = [
  { name: 'bootstrap', port: 6687 },
  { name: 'node1', port: 6688 },
  { name: 'node2', port: 6689 },
  { name: 'node3', port: 6691 }
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

// 创建 OCR key bundle (使用 GraphQL API)
function createOCRKey(cookie, port) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      operationName: "CreateOCRKeyBundle",
      variables: {},
      query: `mutation CreateOCRKeyBundle {
        createOCRKeyBundle {
          ... on CreateOCRKeyBundleSuccess {
            bundle {
              id
              __typename
            }
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
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        if (res.statusCode === 200) {
          const result = JSON.parse(data);
          if (result.data && result.data.createOCRKeyBundle) {
            const bundle = result.data.createOCRKeyBundle.bundle;
            resolve(bundle);
          } else {
            reject(new Error(`GraphQL error: ${JSON.stringify(result.errors || result.data)}`));
          }
        } else {
          reject(new Error(`Failed to create OCR key: ${res.statusCode} - ${data}`));
        }
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

// 为单个节点创建 OCR key
async function createOCRKeyForNode(node) {
  try {
    console.log(`\n正在连接到 Chainlink ${node.name} (端口: ${node.port})...`);

    // 登录
    console.log(`正在登录 ${node.name}...`);
    const cookie = await login(node.port);
    console.log(`✅ ${node.name} 登录成功`);

    // 创建 OCR key
    console.log(`正在为 ${node.name} 创建 OCR key...`);
    const result = await createOCRKey(cookie, node.port);

    console.log(`✅ ${node.name} OCR key 创建成功!`);
    console.log('Key Bundle ID:', result.id);

    return result.id;

  } catch (error) {
    console.error(`\n❌ ${node.name} 创建 OCR key 失败:`, error.message);
    return null;
  }
}

async function main() {
  console.log('========================================');
  console.log('开始为所有 Chainlink 节点创建 OCR key');
  console.log('========================================');

  const ocrKeyBundleIds = {};

  for (const node of nodes) {
    const keyId = await createOCRKeyForNode(node);
    if (keyId) {
      ocrKeyBundleIds[node.name] = keyId;
    }
  }

  console.log('\n========================================');
  console.log('OCR key 创建结果:');
  console.log('========================================');

  for (const node in ocrKeyBundleIds) {
    console.log(`${node}: ${ocrKeyBundleIds[node]}`);
  }

  // 保存 OCR key 信息
  const deploymentDir = path.join(ROOT_DIR, 'deployment');
  if (!fs.existsSync(deploymentDir)) {
    fs.mkdirSync(deploymentDir);
  }

  let deploymentData = {};
  const deploymentFile = path.resolve(deploymentDir, 'chainlink-deployment.json');
  if (fs.existsSync(deploymentFile)) {
    deploymentData = JSON.parse(fs.readFileSync(deploymentFile, 'utf8'));
  }

  deploymentData.ocrKeyBundleIds = ocrKeyBundleIds;
  fs.writeFileSync(deploymentFile, JSON.stringify(deploymentData, null, 2));

  console.log(`\nOCR key 信息已保存到 ${deploymentFile}`);

  if (Object.keys(ocrKeyBundleIds).length === nodes.length) {
    console.log('\n✅ 所有节点的 OCR key 创建成功!');
  } else {
    console.log('\n⚠️  部分节点的 OCR key 创建失败，请检查日志');
  }
}

main();
