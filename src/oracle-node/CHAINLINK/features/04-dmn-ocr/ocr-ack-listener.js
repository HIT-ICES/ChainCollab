const axios = require('axios');
const { ethers } = require('ethers');

const RPC_URL = process.env.RPC_URL || 'http://localhost:8545';
const OCR_AGGREGATOR_ADDRESS = process.env.OCR_AGGREGATOR_ADDRESS;
const DMN_ACK_URL = process.env.DMN_ACK_URL || 'http://localhost:8080/api/dmn/ack';

if (!OCR_AGGREGATOR_ADDRESS) {
  console.error('Missing OCR_AGGREGATOR_ADDRESS');
  process.exit(1);
}

const ABI = [
  'event NewTransmission(uint32 indexed aggregatorRoundId,int192 answer,address transmitter,int192[] observations,bytes observers,bytes32 rawReportContext)',
];

const provider = new ethers.JsonRpcProvider(RPC_URL);
const contract = new ethers.Contract(OCR_AGGREGATOR_ADDRESS, ABI, provider);

async function ackTransmission(event) {
  try {
    const block = await provider.getBlock(event.blockNumber);
    const blockTimestampMs = block ? block.timestamp * 1000 : null;
    await axios.post(
      DMN_ACK_URL,
      {
        aggregatorRoundId: Number(event.args.aggregatorRoundId),
        answer: event.args.answer.toString(),
        transmitter: event.args.transmitter,
        txHash: event.transactionHash,
        blockTimestampMs,
      },
      { timeout: 10000 }
    );
    console.log(
      `Acked round ${event.args.aggregatorRoundId} tx ${event.transactionHash}`
    );
  } catch (err) {
    console.error('Ack failed:', err.message);
  }
}

console.log(`Listening OCR NewTransmission on ${OCR_AGGREGATOR_ADDRESS}`);
contract.on('NewTransmission', (...args) => {
  const event = args[args.length - 1];
  ackTransmission(event);
});
