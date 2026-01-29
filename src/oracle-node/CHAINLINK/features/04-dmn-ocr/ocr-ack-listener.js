const axios = require('axios');
const fs = require('fs');
const path = require('path');
const { ethers } = require('ethers');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const DEPLOYMENT_DIR = path.join(ROOT_DIR, 'deployment');

const RPC_URL = process.env.RPC_URL || 'http://localhost:8545';
const DEFAULT_WS_URL = 'ws://localhost:8546';
const RPC_WS_URL =
  process.env.RPC_WS_URL ||
  DEFAULT_WS_URL ||
  (RPC_URL.startsWith('https://')
    ? RPC_URL.replace('https://', 'wss://')
    : RPC_URL.replace('http://', 'ws://'));
const CHAINLINK_URL = process.env.CHAINLINK_URL || 'http://localhost:6687';
const EI_FILE =
  process.env.EI_FILE ||
  path.join(DEPLOYMENT_DIR, 'external-initiator.json');
const DMN_RAW_BY_HASH_URL = process.env.DMN_RAW_BY_HASH_URL;

function readJson(filePath) {
  if (!fs.existsSync(filePath)) {
    return null;
  }
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (error) {
    console.error(`Failed to read ${filePath}:`, error.message);
    return null;
  }
}

function resolveAggregatorAddress() {
  const ocrDeploymentPath = path.join(DEPLOYMENT_DIR, 'ocr-deployment.json');
  const ocrDeployment = readJson(ocrDeploymentPath);
  if (ocrDeployment?.contractAddress) {
    return ocrDeployment.contractAddress;
  }
  return process.env.OCR_AGGREGATOR_ADDRESS;
}

const OCR_AGGREGATOR_ADDRESS = resolveAggregatorAddress();
if (!OCR_AGGREGATOR_ADDRESS) {
  console.error('Missing OCR aggregator address (ocr-deployment.json not found)');
  process.exit(1);
}

const deployment = readJson(
  path.join(DEPLOYMENT_DIR, 'chainlink-deployment.json')
);
const OCR_WRITER_EXTERNAL_JOB_ID =
  process.env.OCR_WRITER_EXTERNAL_JOB_ID || deployment?.ocrWriterExternalJobId;
if (!OCR_WRITER_EXTERNAL_JOB_ID) {
  console.error('Missing OCR_WRITER_EXTERNAL_JOB_ID (create writer job first)');
  process.exit(1);
}

const eiInfo = readJson(EI_FILE);
const EI_ACCESS_KEY = process.env.EI_ACCESS_KEY || eiInfo?.accessKey;
const EI_SECRET = process.env.EI_SECRET || eiInfo?.secret;
if (!EI_ACCESS_KEY || !EI_SECRET) {
  console.error('Missing EI credentials (run create-external-initiator.js)');
  process.exit(1);
}
if (!DMN_RAW_BY_HASH_URL) {
  console.error('Missing DMN_RAW_BY_HASH_URL for writer webhook payload');
  process.exit(1);
}

const ABI = [
  'event NewTransmission(uint32 indexed aggregatorRoundId,int192 answer,address transmitter,int192[] observations,bytes observers,bytes32 rawReportContext)',
];

function buildFetchUrl(hash) {
  const separator = DMN_RAW_BY_HASH_URL.includes('?') ? '&' : '?';
  return `${DMN_RAW_BY_HASH_URL}${separator}hash=${encodeURIComponent(hash)}`;
}

async function triggerWebhook(hash) {
  const fetchURL = buildFetchUrl(hash);
  await axios.post(
    `${CHAINLINK_URL}/v2/jobs/${OCR_WRITER_EXTERNAL_JOB_ID}/runs`,
    { data: { hash, fetchURL } },
    {
      headers: {
        'Content-Type': 'application/json',
        'X-Chainlink-EA-AccessKey': EI_ACCESS_KEY,
        'X-Chainlink-EA-Secret': EI_SECRET,
      },
      timeout: 10000,
    }
  );
}

let shuttingDown = false;
let reconnectTimer = null;

function scheduleReconnect() {
  if (shuttingDown || reconnectTimer) {
    return;
  }
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    startListener();
  }, 3000);
}

function startListener() {
  if (!RPC_WS_URL || RPC_WS_URL.startsWith('http')) {
    console.error('Missing RPC_WS_URL for WebSocket subscription');
    process.exit(1);
  }

  const provider = new ethers.WebSocketProvider(RPC_WS_URL);
  const contract = new ethers.Contract(OCR_AGGREGATOR_ADDRESS, ABI, provider);

  const ws = provider._websocket || provider.websocket;
  if (ws) {
    ws.on('close', () => {
      console.error('WebSocket closed, reconnecting...');
      try {
        contract.removeAllListeners();
      } catch (error) {
        console.error('Failed to remove listeners:', error.message);
      }
      scheduleReconnect();
    });
    ws.on('error', (error) => {
      console.error('WebSocket error:', error.message || error);
      scheduleReconnect();
    });
  }

  console.log(`Listening OCR NewTransmission on ${OCR_AGGREGATOR_ADDRESS}`);
  contract.on('NewTransmission', async (...args) => {
    const event = args[args.length - 1];
    try {
      const hash = event.args.answer.toString();
      await triggerWebhook(hash);
      console.log(`Triggered writer job for hash=${hash}`);
    } catch (err) {
      const status = err?.response?.status;
      const data = err?.response?.data;
      if (status || data) {
        console.error(
          'Trigger failed:',
          status ? `status=${status}` : err.message,
          data ? `body=${JSON.stringify(data)}` : ''
        );
      } else {
        console.error('Trigger failed:', err.message);
      }
    }
  });
}

process.on('SIGINT', () => {
  shuttingDown = true;
  process.exit(0);
});

process.on('SIGTERM', () => {
  shuttingDown = true;
  process.exit(0);
});

startListener();
