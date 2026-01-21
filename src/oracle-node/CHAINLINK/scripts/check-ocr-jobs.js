const fs = require('fs');
const http = require('http');

const username = 'admin@chain.link';
const password = 'change-me-strong';

const nodes = [
  { name: 'bootstrap', port: 6687, isBootstrap: true, container: 'chainlink-bootstrap' },
  { name: 'node1', port: 6688, isBootstrap: false, container: 'chainlink-node1' },
  { name: 'node2', port: 6689, isBootstrap: false, container: 'chainlink-node2' },
  { name: 'node3', port: 6691, isBootstrap: false, container: 'chainlink-node3' },
  { name: 'node4', port: 6692, isBootstrap: false, container: 'chainlink-node4' }
];

function readJson(path, label) {
  if (!fs.existsSync(path)) {
    console.error(`❌ 找不到 ${label}: ${path}`);
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(path, 'utf8'));
}

function normalizeAddress(value) {
  if (!value) return '';
  return value.toLowerCase();
}

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

function getJobs(cookie, port) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'localhost',
      port: port,
      path: '/v2/jobs?size=200',
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
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
          reject(new Error(`Failed to fetch jobs: ${res.statusCode} - ${data}`));
        }
      });
    });

    req.on('error', reject);
    req.end();
  });
}

function getJobRuns(cookie, port, jobId) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'localhost',
      port: port,
      path: `/v2/jobs/${jobId}/runs?size=50`,
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
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
          reject(new Error(`Failed to fetch job runs: ${res.statusCode} - ${data}`));
        }
      });
    });

    req.on('error', reject);
    req.end();
  });
}

function findNodeInfo(nodeInfo, name) {
  return nodeInfo.find((node) => node.name === name) || null;
}

function pickOCRJobs(jobs) {
  const list = Array.isArray(jobs.data) ? jobs.data : [];
  return list.filter((job) => {
    const attrs = job.attributes || {};
    return attrs.type === 'offchainreporting';
  });
}

function summarizeJob(job) {
  const attrs = job.attributes || {};
  const spec = attrs.offChainReportingOracleSpec || attrs.bootstrapSpec || attrs;
  return {
    id: job.id,
    name: attrs.name,
    externalJobID: attrs.externalJobID,
    isBootstrapPeer: spec.isBootstrapPeer,
    contractAddress: spec.contractAddress,
    transmitterAddress: spec.transmitterAddress,
    keyBundleID: spec.keyBundleID
  };
}

function extractObservationURL() {
  if (process.env.OCR_OBSERVATION_URL) {
    return process.env.OCR_OBSERVATION_URL.trim();
  }

  const path = require('path');
  const specPath = path.resolve(__dirname, '..', 'config', 'job-spec-ocr.toml');
  if (!fs.existsSync(specPath)) {
    return null;
  }
  const content = fs.readFileSync(specPath, 'utf8');
  const match = content.match(/url\\s*=\\s*\"(http[^\"]+)\"/);
  return match ? match[1] : null;
}

function checkContainerURL(container, url) {
  const { execSync } = require('child_process');
  if (!url) {
    return { ok: false, output: 'missing URL' };
  }
  try {
    const output = execSync(`docker exec ${container} curl -s --max-time 3 ${url}`, {
      stdio: ['ignore', 'pipe', 'pipe']
    }).toString().trim();
    return { ok: output.length > 0, output };
  } catch (error) {
    return { ok: false, output: error.stderr ? error.stderr.toString().trim() : error.message };
  }
}

function validateJob(job, expected, isBootstrap) {
  const result = [];
  if (normalizeAddress(job.contractAddress) !== normalizeAddress(expected.contractAddress)) {
    result.push(`contractAddress mismatch (expected ${expected.contractAddress}, got ${job.contractAddress || 'null'})`);
  }

  if (job.keyBundleID !== expected.keyBundleID) {
    result.push(`keyBundleID mismatch (expected ${expected.keyBundleID}, got ${job.keyBundleID || 'null'})`);
  }

  if (!isBootstrap) {
    if (normalizeAddress(job.transmitterAddress) !== normalizeAddress(expected.transmitterAddress)) {
      result.push(`transmitterAddress mismatch (expected ${expected.transmitterAddress}, got ${job.transmitterAddress || 'null'})`);
    }
  }

  if (Boolean(job.isBootstrapPeer) !== Boolean(isBootstrap)) {
    result.push(`isBootstrapPeer mismatch (expected ${isBootstrap}, got ${job.isBootstrapPeer})`);
  }

  return result;
}

async function main() {
  const nodeInfo = readJson('deployment/node-info.json', 'node-info.json');
  const ocrDeployment = readJson('deployment/ocr-deployment.json', 'ocr-deployment.json');
  const contractAddress = ocrDeployment.contractAddress;
  const observationURL = extractObservationURL();

  console.log('=== OCR Job 检查 ===');
  console.log('合约地址:', contractAddress);
  if (observationURL) {
    console.log('数据源 URL:', observationURL);
  }

  for (const node of nodes) {
    console.log(`\n--- ${node.name} (port ${node.port}) ---`);
    let cookie;
    try {
      cookie = await login(node.port);
    } catch (error) {
      console.error(`❌ 登录失败: ${error.message}`);
      continue;
    }

    let jobs;
    try {
      jobs = await getJobs(cookie, node.port);
    } catch (error) {
      console.error(`❌ 获取 jobs 失败: ${error.message}`);
      continue;
    }

    const ocrJobs = pickOCRJobs(jobs);
    if (ocrJobs.length === 0) {
      console.error('❌ 未找到 OCR job');
      continue;
    }

    const expectedNode = findNodeInfo(nodeInfo, node.name);
    if (!expectedNode) {
      console.error('❌ node-info.json 中未找到对应节点信息');
      continue;
    }

    const expected = {
      contractAddress: contractAddress,
      keyBundleID: expectedNode.ocrKeyBundleId,
      transmitterAddress: expectedNode.ethAddress
    };

    for (const job of ocrJobs) {
      const summary = summarizeJob(job);
      console.log(`Job: ${summary.name} (${summary.id})`);
      console.log(`  externalJobID: ${summary.externalJobID}`);
      console.log(`  isBootstrapPeer: ${summary.isBootstrapPeer}`);
      console.log(`  contractAddress: ${summary.contractAddress}`);
      console.log(`  transmitterAddress: ${summary.transmitterAddress}`);
      console.log(`  keyBundleID: ${summary.keyBundleID}`);

      const issues = validateJob(summary, expected, node.isBootstrap);
      if (issues.length === 0) {
        console.log('  ✅ 配置一致');
      } else {
        console.log('  ⚠️  配置不一致:');
        for (const issue of issues) {
          console.log(`    - ${issue}`);
        }
      }

      if (!node.isBootstrap) {
        try {
          const runs = await getJobRuns(cookie, node.port, summary.id);
          const runCount = Array.isArray(runs.data) ? runs.data.length : 0;
          console.log(`  Runs(最近50): ${runCount}`);
        } catch (error) {
          console.log(`  Runs 获取失败: ${error.message}`);
        }
      }
    }

    if (!node.isBootstrap && node.container) {
      const connectivity = checkContainerURL(node.container, observationURL);
      if (connectivity.ok) {
        console.log(`  ✅ 容器内可访问数据源`);
      } else {
        console.log(`  ⚠️  容器内无法访问数据源: ${connectivity.output}`);
      }
    }
  }
}

main().catch((error) => {
  console.error('❌ 脚本执行失败:', error.message);
  process.exit(1);
});
