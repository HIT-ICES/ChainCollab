// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract CrossChainAdapter {
    struct CallResult {
        bool success;
        bytes data;
    }

    address public owner;
    uint256 public threshold;
    uint256 public relayerCount;

    mapping(address => bool) public relayers;
    mapping(bytes32 => bool) public processed;
    mapping(bytes32 => CallResult) private results;
    uint64 public nextNonce;

    event RelayerUpdated(address indexed relayer, bool active);
    event ThresholdUpdated(uint256 threshold);
    event CrossChainCallReceived(
        bytes32 indexed messageId,
        uint64 indexed srcChainId,
        uint64 indexed dstChainId,
        address target,
        bool success,
        bytes returnData
    );
    event XCallRequested(
        uint64 indexed srcChainId,
        uint64 indexed dstChainId,
        uint64 nonce,
        address target,
        uint256 value,
        bytes callData
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor(address[] memory initialRelayers, uint256 initialThreshold) {
        owner = msg.sender;
        _setRelayers(initialRelayers, true);
        _setThreshold(initialThreshold);
    }

    function setRelayers(address[] calldata relayers_, bool active) external onlyOwner {
        _setRelayers(relayers_, active);
    }

    function setThreshold(uint256 newThreshold) external onlyOwner {
        _setThreshold(newThreshold);
    }

    function receiveCrossChainCall(
        uint64 srcChainId,
        uint64 dstChainId,
        uint64 nonce,
        address target,
        uint256 value,
        bytes calldata callData,
        bytes[] calldata signatures
    ) external returns (bytes32 messageId, bool success, bytes memory returnData) {
        require(dstChainId == uint64(block.chainid), "wrong destination");
        messageId = computeMessageHash(srcChainId, dstChainId, nonce, target, value, callData);
        require(!processed[messageId], "already processed");
        _verifyThreshold(messageId, signatures);
        processed[messageId] = true;

        (success, returnData) = target.call{value: value}(callData);
        results[messageId] = CallResult({success: success, data: returnData});

        emit CrossChainCallReceived(messageId, srcChainId, dstChainId, target, success, returnData);
    }

    function requestCrossChainCall(
        uint64 dstChainId,
        address target,
        uint256 value,
        bytes calldata callData
    ) external returns (uint64 nonce) {
        require(target != address(0), "bad target");
        nonce = nextNonce;
        nextNonce += 1;
        emit XCallRequested(uint64(block.chainid), dstChainId, nonce, target, value, callData);
    }

    function computeMessageHash(
        uint64 srcChainId,
        uint64 dstChainId,
        uint64 nonce,
        address target,
        uint256 value,
        bytes calldata callData
    ) public view returns (bytes32) {
        return keccak256(
            abi.encodePacked(
                "XCALL",
                address(this),
                srcChainId,
                dstChainId,
                nonce,
                target,
                value,
                keccak256(callData)
            )
        );
    }

    function getResult(bytes32 messageId) external view returns (bool, bytes memory) {
        CallResult storage result = results[messageId];
        return (result.success, result.data);
    }

    function _setRelayers(address[] memory relayers_, bool active) internal {
        for (uint256 i = 0; i < relayers_.length; i++) {
            address relayer = relayers_[i];
            require(relayer != address(0), "zero address");
            if (active && !relayers[relayer]) {
                relayers[relayer] = true;
                relayerCount += 1;
                emit RelayerUpdated(relayer, true);
            } else if (!active && relayers[relayer]) {
                relayers[relayer] = false;
                relayerCount -= 1;
                emit RelayerUpdated(relayer, false);
            }
        }
        require(relayerCount >= threshold, "threshold too high");
    }

    function _setThreshold(uint256 newThreshold) internal {
        require(newThreshold > 0, "threshold zero");
        require(relayerCount == 0 || newThreshold <= relayerCount, "threshold too high");
        threshold = newThreshold;
        emit ThresholdUpdated(newThreshold);
    }

    function _verifyThreshold(bytes32 messageId, bytes[] calldata signatures) internal view {
        require(signatures.length >= threshold, "not enough signatures");
        bytes32 digest = _toEthSignedMessageHash(messageId);
        address[] memory seen = new address[](signatures.length);
        uint256 validCount = 0;

        for (uint256 i = 0; i < signatures.length; i++) {
            address signer = _recoverSigner(digest, signatures[i]);
            if (signer == address(0)) {
                continue;
            }
            if (!relayers[signer]) {
                continue;
            }
            if (_isDuplicate(seen, signer)) {
                continue;
            }
            seen[validCount] = signer;
            validCount += 1;
            if (validCount >= threshold) {
                break;
            }
        }
        require(validCount >= threshold, "insufficient valid signatures");
    }

    function _isDuplicate(address[] memory seen, address signer) internal pure returns (bool) {
        for (uint256 i = 0; i < seen.length; i++) {
            if (seen[i] == signer) {
                return true;
            }
        }
        return false;
    }

    function _recoverSigner(bytes32 digest, bytes memory signature) internal pure returns (address) {
        require(signature.length == 65, "bad signature length");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(signature, 0x20))
            s := mload(add(signature, 0x40))
            v := byte(0, mload(add(signature, 0x60)))
        }
        if (v < 27) {
            v += 27;
        }
        require(v == 27 || v == 28, "bad signature v");
        return ecrecover(digest, v, r, s);
    }

    function _toEthSignedMessageHash(bytes32 hash) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", hash));
    }

    receive() external payable {}
}
