// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract BookDonation {
    // 1. DATA STRUKTUR
    struct Donation {
        uint id;
        uint campaignId;
        address donor;
        uint amount;       // Jumlah ETH donasi (bisa dianggap sebagai biaya operasional/nilai buku)
        string bookDetails; // Deskripsi buku yang didonasikan
        uint timestamp;
    }

    struct Campaign {
        uint id;
        address creator;
        uint targetAmount;
        uint currentAmount;
        bool isOpen;
    }

    // 2. PENYIMPANAN DATA
    uint public campaignCount = 0;
    uint public donationCount = 0;
    
    mapping(uint => Campaign) public campaigns;
    mapping(uint => Donation) public donations; // Menyimpan detail tiap donasi
    
    // Mapping agar kita bisa cari donasi apa saja di kampanye X
    mapping(uint => uint[]) public campaignToDonationIds;

    // 3. EVENT (Untuk Log Admin)
    event CampaignCreated(uint id, address creator, uint target);
    event NewDonation(uint id, uint campaignId, address donor, uint amount, string details);

    // 4. FUNGSI UTAMA

    // Kreator membuat kampanye
    function createCampaign(uint _targetAmount) public {
        campaignCount++;
        campaigns[campaignCount] = Campaign(campaignCount, msg.sender, _targetAmount, 0, true);
        emit CampaignCreated(campaignCount, msg.sender, _targetAmount);
    }

    // Donatur mengirim donasi
    function donate(uint _campaignId, string memory _bookDetails) public payable {
        require(campaigns[_campaignId].isOpen, "Kampanye sudah ditutup");
        
        donationCount++;
        
        // Simpan data donasi
        donations[donationCount] = Donation(
            donationCount,
            _campaignId,
            msg.sender,
            msg.value,
            _bookDetails,
            block.timestamp
        );

        // Update total terkumpul di kampanye
        campaigns[_campaignId].currentAmount += msg.value;
        
        // Link donasi ke kampanye
        campaignToDonationIds[_campaignId].push(donationCount);

        emit NewDonation(donationCount, _campaignId, msg.sender, msg.value, _bookDetails);
    }
}