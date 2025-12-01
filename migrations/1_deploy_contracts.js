const BukuDonasi = artifacts.require("BukuDonasi");

module.exports = function (deployer) {
  deployer.deploy(BukuDonasi);
};