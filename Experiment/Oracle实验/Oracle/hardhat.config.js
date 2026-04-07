require("@nomicfoundation/hardhat-ethers");

module.exports = {
  paths: {
    sources: "./src/contract"
  },
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  }
};
