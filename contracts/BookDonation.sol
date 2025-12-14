// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract BookDonation {

    address public owner;
    uint public campaignFee = 0.01 ether;

    constructor() {
        owner = msg.sender;
    }

    struct Donation {
        uint id;
        uint campaignId;
        address donor;
        uint amount;
        string bookDetails;
        uint timestamp;
    }

    struct Campaign {
        uint id;
        address creator;
        uint targetAmount;
        uint currentAmount;
        bool isOpen;
    }

    uint public campaignCount = 0;
    uint public donationCount = 0;

    mapping(uint => Campaign) public campaigns;
    mapping(uint => Donation) public donations;
    mapping(uint => uint[]) public campaignToDonationIds;

    event CampaignCreated(uint id, address creator, uint target);
    event NewDonation(uint id, uint campaignId, address donor, uint amount, string details);

    // ✅ CREATE CAMPAIGN + BAYAR FEE
    function createCampaignPaid(uint _targetAmount) public payable {
        require(msg.value >= campaignFee, "Biaya campaign kurang");

        campaignCount++;
        campaigns[campaignCount] = Campaign(
            campaignCount,
            msg.sender,
            _targetAmount,
            0,
            true
        );

        emit CampaignCreated(campaignCount, msg.sender, _targetAmount);
    }

function approveCampaignAndPay(uint _campaignId) public {
    require(msg.sender == owner, "Bukan admin");

    Campaign storage c = campaigns[_campaignId];

    require(c.isOpen, "Campaign invalid");

    // ⛔ Cegah approve ulang
    c.isOpen = false;

    // ✅ Transfer fee dari CONTRACT ke ADMIN
    payable(owner).transfer(campaignFee);
}


    // ⛔ DONATE TETAP
    function donate(uint _campaignId, string memory _bookDetails) public payable {
        require(campaigns[_campaignId].isOpen, "Kampanye sudah ditutup");

        donationCount++;

        donations[donationCount] = Donation(
            donationCount,
            _campaignId,
            msg.sender,
            msg.value,
            _bookDetails,
            block.timestamp
        );

        campaigns[_campaignId].currentAmount += msg.value;
        campaignToDonationIds[_campaignId].push(donationCount);

        emit NewDonation(donationCount, _campaignId, msg.sender, msg.value, _bookDetails);
    }

    function withdrawFees() public {
        require(msg.sender == owner, "Bukan admin");
        payable(owner).transfer(address(this).balance);
    }
}
