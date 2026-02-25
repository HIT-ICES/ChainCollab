// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract IndustrialIoTReceiver {
    struct Telemetry {
        uint256 fromChainId;
        bytes32 deviceId;
        string lineId;
        int256 temperatureMilliC;
        uint256 vibrationUm;
        uint256 pressureKpa;
        uint256 riskScore;
        bool alert;
        uint256 sampleTs;
        uint256 receivedAt;
    }

    struct Decision {
        uint256 fromChainId;
        bytes32 deviceId;
        uint256 riskScore;
        string decision;
        uint256 sampleTs;
        uint256 receivedAt;
    }

    mapping(bytes32 => Telemetry) public latestTelemetry;
    mapping(bytes32 => Decision) public latestDecision;

    mapping(bytes32 => uint256) public telemetryCount;
    mapping(bytes32 => uint256) public decisionCount;

    uint256 public totalTelemetry;
    uint256 public totalDecision;

    event TelemetryIngested(
        bytes32 indexed deviceId,
        uint256 indexed fromChainId,
        uint256 riskScore,
        bool alert,
        uint256 sampleTs
    );

    event DecisionIngested(
        bytes32 indexed deviceId,
        uint256 indexed fromChainId,
        uint256 riskScore,
        string decision,
        uint256 sampleTs
    );

    function ingestTelemetry(
        uint256 fromChainId,
        bytes32 deviceId,
        string calldata lineId,
        int256 temperatureMilliC,
        uint256 vibrationUm,
        uint256 pressureKpa,
        uint256 sampleTs
    ) external returns (uint256 riskScore, bool alert) {
        require(deviceId != bytes32(0), "invalid device");
        require(sampleTs > latestTelemetry[deviceId].sampleTs, "stale sample");

        riskScore = _computeRisk(temperatureMilliC, vibrationUm, pressureKpa);
        alert = riskScore >= 80;

        latestTelemetry[deviceId] = Telemetry({
            fromChainId: fromChainId,
            deviceId: deviceId,
            lineId: lineId,
            temperatureMilliC: temperatureMilliC,
            vibrationUm: vibrationUm,
            pressureKpa: pressureKpa,
            riskScore: riskScore,
            alert: alert,
            sampleTs: sampleTs,
            receivedAt: block.timestamp
        });

        telemetryCount[deviceId] += 1;
        totalTelemetry += 1;

        emit TelemetryIngested(deviceId, fromChainId, riskScore, alert, sampleTs);
    }

    function ingestMaintenanceDecision(
        uint256 fromChainId,
        bytes32 deviceId,
        uint256 riskScore,
        string calldata decision,
        uint256 sampleTs
    ) external returns (bool) {
        require(deviceId != bytes32(0), "invalid device");
        require(bytes(decision).length > 0, "empty decision");

        Decision storage current = latestDecision[deviceId];
        require(sampleTs >= current.sampleTs, "stale decision");

        latestDecision[deviceId] = Decision({
            fromChainId: fromChainId,
            deviceId: deviceId,
            riskScore: riskScore,
            decision: decision,
            sampleTs: sampleTs,
            receivedAt: block.timestamp
        });

        decisionCount[deviceId] += 1;
        totalDecision += 1;

        emit DecisionIngested(deviceId, fromChainId, riskScore, decision, sampleTs);
        return true;
    }

    function _computeRisk(
        int256 temperatureMilliC,
        uint256 vibrationUm,
        uint256 pressureKpa
    ) internal pure returns (uint256) {
        // Baseline assumptions for rotating machinery line:
        // - Temperature baseline: 65C (65000 milli-C)
        // - Pressure baseline: 110 kPa
        // - Vibration naturally non-negative
        uint256 tempDeviation = _absDiff(temperatureMilliC, 65000);
        uint256 pressureDeviation = _absDiffInt(uint256(pressureKpa), 110);

        uint256 tempPart = tempDeviation / 1000; // every 1C contributes 1
        uint256 vibrationPart = vibrationUm / 8; // sensitivity to vibration spikes
        uint256 pressurePart = pressureDeviation * 2;

        return tempPart + vibrationPart + pressurePart;
    }

    function _absDiff(int256 a, int256 b) internal pure returns (uint256) {
        if (a >= b) {
            return uint256(a - b);
        }
        return uint256(b - a);
    }

    function _absDiffInt(uint256 a, uint256 b) internal pure returns (uint256) {
        return a >= b ? a - b : b - a;
    }
}
