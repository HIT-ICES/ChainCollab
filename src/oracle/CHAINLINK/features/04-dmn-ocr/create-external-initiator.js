const axios = require('axios');
const fs = require('fs');
const path = require('path');

const CHAINLINK_URL = process.env.CHAINLINK_URL || 'http://localhost:6687';
const CHAINLINK_EMAIL = process.env.CHAINLINK_EMAIL || 'admin@chain.link';
const CHAINLINK_PASSWORD = process.env.CHAINLINK_PASSWORD || 'change-me-strong';

const EI_NAME = process.env.EI_NAME || 'dmn-ocr-ei';
const EI_URL = process.env.EI_URL || 'http://localhost:8089';

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const DEPLOYMENT_DIR = path.join(ROOT_DIR, 'deployment');
const OUTPUT_PATH =
  process.env.EI_OUTPUT_PATH ||
  path.join(DEPLOYMENT_DIR, 'external-initiator.json');

async function login() {
  const response = await axios.post(`${CHAINLINK_URL}/sessions`, {
    email: CHAINLINK_EMAIL,
    password: CHAINLINK_PASSWORD,
  });
  const cookies = response.headers['set-cookie'];
  if (!cookies) {
    throw new Error('no session cookie');
  }
  return cookies.join('; ');
}

async function createExternalInitiator(cookie) {
  const response = await axios.post(
    `${CHAINLINK_URL}/v2/external_initiators`,
    {
      name: EI_NAME,
      url: EI_URL,
    },
    {
      headers: {
        'Content-Type': 'application/json',
        Cookie: cookie,
      },
      timeout: 10000,
    }
  );
  return response.data;
}

function writeOutput(data) {
  try {
    fs.mkdirSync(DEPLOYMENT_DIR, { recursive: true });
    fs.writeFileSync(OUTPUT_PATH, JSON.stringify(data, null, 2), 'utf8');
    console.log(`✅ Saved external initiator to ${OUTPUT_PATH}`);
  } catch (error) {
    console.error('❌ Failed to write output file:', error.message);
  }
}

async function main() {
  try {
    const cookie = await login();
    const data = await createExternalInitiator(cookie);
    console.log('✅ External Initiator created:');
    console.log(JSON.stringify(data, null, 2));
    const attrs = data?.data?.attributes || {};
    writeOutput({
      name: EI_NAME,
      url: EI_URL,
      accessKey: attrs.incomingAccessKey || data?.accessKey,
      secret: attrs.incomingSecret || data?.secret,
      outgoingToken: attrs.outgoingToken,
      outgoingSecret: attrs.outgoingSecret,
      createdAt: new Date().toISOString(),
    });
  } catch (error) {
    const status = error?.response?.status;
    const body = error?.response?.data;
    if (status || body) {
      console.error(
        '❌ Create failed:',
        status ? `status=${status}` : error.message,
        body ? `body=${JSON.stringify(body)}` : ''
      );
      process.exit(1);
    }
    console.error('❌ Create failed:', error.message);
    process.exit(1);
  }
}

main();
