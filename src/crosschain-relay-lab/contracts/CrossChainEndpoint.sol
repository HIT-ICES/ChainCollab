// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract CrossChainEndpoint {
    address public owner;

    mapping(address => bool) public relayers;
    mapping(address => bool) public allowedTargets;
    mapping(address => uint256) public nonces;
    mapping(bytes32 => bool) public executed;

    event OwnerTransferred(address indexed oldOwner, address indexed newOwner);
    event RelayerUpdated(address indexed relayer, bool enabled);
    event AllowedTargetUpdated(address indexed target, bool enabled);

    event RelayRequested(
        bytes32 indexed msgId,
        uint256 indexed dstChainId,
        address indexed dstReceiver,
        address srcSender,
        bytes payload,
        uint256 nonce
    );

    event RelayExecuted(
        bytes32 indexed msgId,
        bool ok,
        bytes returnData,
        address relayer
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyRelayer() {
        require(relayers[msg.sender], "not relayer");
        _;
    }

    constructor() {
        owner = msg.sender;
        relayers[msg.sender] = true;
        emit RelayerUpdated(msg.sender, true);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero owner");
        address old = owner;
        owner = newOwner;
        emit OwnerTransferred(old, newOwner);
    }

    function setRelayer(address relayer, bool enabled) external onlyOwner {
        require(relayer != address(0), "zero relayer");
        relayers[relayer] = enabled;
        emit RelayerUpdated(relayer, enabled);
    }

    function setAllowedTarget(address target, bool enabled) external onlyOwner {
        require(target != address(0), "zero target");
        allowedTargets[target] = enabled;
        emit AllowedTargetUpdated(target, enabled);
    }

    function computeMessageId(
        uint256 srcChainId,
        address srcEndpoint,
        address srcSender,
        uint256 dstChainId,
        address dstReceiver,
        uint256 nonce,
        bytes memory payload
    ) public pure returns (bytes32) {
        return keccak256(
            abi.encode(
                srcChainId,
                srcEndpoint,
                srcSender,
                dstChainId,
                dstReceiver,
                nonce,
                payload
            )
        );
    }

    function sendMessage(
        uint256 dstChainId,
        address dstReceiver,
        bytes calldata payload
    ) external returns (bytes32 msgId) {
        require(dstChainId > 0, "invalid dst chain");
        require(dstReceiver != address(0), "zero dst receiver");
        require(payload.length > 0, "empty payload");

        uint256 nonce = ++nonces[msg.sender];
        msgId = computeMessageId(
            block.chainid,
            address(this),
            msg.sender,
            dstChainId,
            dstReceiver,
            nonce,
            payload
        );

        emit RelayRequested(
            msgId,
            dstChainId,
            dstReceiver,
            msg.sender,
            payload,
            nonce
        );
    }

    function executeMessage(
        bytes32 msgId,
        uint256 srcChainId,
        address srcEndpoint,
        address srcSender,
        address dstReceiver,
        uint256 nonce,
        bytes calldata payload
    ) external onlyRelayer returns (bool ok, bytes memory returnData) {
        require(!executed[msgId], "already executed");
        require(allowedTargets[dstReceiver], "target not allowed");

        bytes32 expected = computeMessageId(
            srcChainId,
            srcEndpoint,
            srcSender,
            block.chainid,
            dstReceiver,
            nonce,
            payload
        );
        require(expected == msgId, "invalid message");

        (ok, returnData) = dstReceiver.call(payload);
        if (ok) {
            executed[msgId] = true;
        }

        emit RelayExecuted(msgId, ok, returnData, msg.sender);
    }
}
