import "@nomicfoundation/hardhat-toolbox";

const localhostUrl = process.env.RPC_URL || "http://127.0.0.1:8545";
const anvilUrl = process.env.ANVIL_RPC_URL || "http://127.0.0.1:8545";

export default {
  solidity: "0.8.20",
  networks: {
    localhost: {
      url: localhostUrl
    },
    anvil: {
      url: anvilUrl
    }
  }
};
