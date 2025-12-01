// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract BukuDonasi {
    address public admin;
    uint public donationCount = 0;

    struct Donation {
        uint id;
        address donor;
        string bookTitle;
        string status; // "Belum Dikirim", "Dalam Pengiriman", "Sampai ke Kreator"
        uint timestamp;
    }

    mapping(uint => Donation) public donations;
    mapping(address => uint[]) public donorDonations;

    event DonationCreated(uint id, address donor, string bookTitle);
    event StatusUpdated(uint id, string newStatus);

    constructor() {
        admin = msg.sender; // Pembuat contract otomatis jadi admin
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Hanya Admin yang boleh akses");
        _;
    }

    function donateBook(string memory _bookTitle) public {
        donationCount++;
        donations[donationCount] = Donation(donationCount, msg.sender, _bookTitle, "Belum Dikirim", block.timestamp);
        donorDonations[msg.sender].push(donationCount);
        emit DonationCreated(donationCount, msg.sender, _bookTitle);
    }

    function updateStatus(uint _id, string memory _newStatus) public {
        // Bisa dimodifikasi agar Kreator juga bisa update jika diperlukan
        // Untuk saat ini kita buat Admin atau user terkait yang bisa update (logic sederhana)
        Donation storage d = donations[_id];
        d.status = _newStatus;
        emit StatusUpdated(_id, _newStatus);
    }

    function getDonation(uint _id) public view returns (uint, address, string memory, string memory, uint) {
        Donation memory d = donations[_id];
        return (d.id, d.donor, d.bookTitle, d.status, d.timestamp);
    }
}