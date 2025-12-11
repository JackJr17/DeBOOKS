module.exports = {
  /**
   * Networks define how you connect to your ethereum client.
   */

  networks: {
    // Konfigurasi untuk Ganache (Local Blockchain)
    development: {
      host: "127.0.0.1",     // Localhost (IP komputer sendiri)
      port: 7545,            // PORT PENTING! Sesuaikan dengan aplikasi Ganache (GUI biasanya 7545)
      network_id: "*",       // Match any network id
    },
  },

  // Konfigurasi Compiler Solidity
  compilers: {
    solc: {
      version: "0.8.21",      // Tetap pakai versi 0.8.21
      settings: {
        optimizer: {
          enabled: true,
          runs: 200
        },
        evmVersion: "paris"   // <--- INI SOLUSINYA! (Mematikan PUSH0)
      }
    }
  }
};