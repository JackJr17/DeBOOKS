const BookDonation = artifacts.require("BookDonation");

module.exports = function (deployer) {
  deployer.deploy(BookDonation);
};