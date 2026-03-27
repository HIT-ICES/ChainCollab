// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SlotRegistry {
    struct Slot {
        bool exists;
        string value;
        uint64 updatedAt;
    }

    address public owner;
    mapping(address => bool) public writers;
    mapping(bytes32 => Slot) private slots;

    event WriterUpdated(address indexed writer, bool enabled);
    event SlotUpdated(bytes32 indexed slotKey, string value, uint64 updatedAt, string source);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyWriter() {
        require(writers[msg.sender], "not writer");
        _;
    }

    constructor() {
        owner = msg.sender;
        writers[msg.sender] = true;
        emit WriterUpdated(msg.sender, true);
    }

    function setWriter(address writer, bool enabled) external onlyOwner {
        require(writer != address(0), "zero writer");
        writers[writer] = enabled;
        emit WriterUpdated(writer, enabled);
    }

    function setSlot(
        bytes32 slotKey,
        string calldata value,
        string calldata source
    ) external onlyWriter {
        require(slotKey != bytes32(0), "invalid slot key");
        Slot storage s = slots[slotKey];
        s.exists = true;
        s.value = value;
        s.updatedAt = uint64(block.timestamp);
        emit SlotUpdated(slotKey, value, s.updatedAt, source);
    }

    function getSlot(
        bytes32 slotKey
    ) external view returns (bool exists, string memory value, uint64 updatedAt) {
        Slot storage s = slots[slotKey];
        return (s.exists, s.value, s.updatedAt);
    }
}
