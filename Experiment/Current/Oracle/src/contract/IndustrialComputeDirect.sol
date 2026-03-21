// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract IndustrialComputeDirect {
    uint256 public lastResult;
    event DirectComputed(bytes32 indexed taskType, uint256 result);

    function calcAvailabilityBps(
        uint256 runMinutes,
        uint256 plannedMinutes
    ) external returns (uint256) {
        require(plannedMinutes > 0, "planned=0");
        uint256 result = (runMinutes * 10000) / plannedMinutes;
        lastResult = result;
        emit DirectComputed("availability_bps", result);
        return result;
    }

    function calcPerformanceBps(
        uint256 idealCycleMs,
        uint256 totalCount,
        uint256 runTimeMs
    ) external returns (uint256) {
        require(runTimeMs > 0, "runtime=0");
        uint256 result = (idealCycleMs * totalCount * 10000) / runTimeMs;
        lastResult = result;
        emit DirectComputed("performance_bps", result);
        return result;
    }

    function calcQualityBps(
        uint256 goodCount,
        uint256 totalCount
    ) external returns (uint256) {
        require(totalCount > 0, "total=0");
        uint256 result = (goodCount * 10000) / totalCount;
        lastResult = result;
        emit DirectComputed("quality_bps", result);
        return result;
    }

    function calcOEEBps(
        uint256 availabilityBps,
        uint256 performanceBps,
        uint256 qualityBps
    ) external returns (uint256) {
        uint256 ap = (availabilityBps * performanceBps) / 10000;
        uint256 result = (ap * qualityBps) / 10000;
        lastResult = result;
        emit DirectComputed("oee_bps", result);
        return result;
    }

    function calcMTBFMinutes(
        uint256 totalRunMinutes,
        uint256 failureCount
    ) external returns (uint256) {
        uint256 result = failureCount == 0 ? totalRunMinutes : totalRunMinutes / failureCount;
        lastResult = result;
        emit DirectComputed("mtbf_minutes", result);
        return result;
    }

    function calcMTTRMinutes(
        uint256 totalRepairMinutes,
        uint256 repairCount
    ) external returns (uint256) {
        uint256 result = repairCount == 0 ? 0 : totalRepairMinutes / repairCount;
        lastResult = result;
        emit DirectComputed("mttr_minutes", result);
        return result;
    }

    function calcAvailabilityFromMTBFMTTRBps(
        uint256 mtbfMinutes,
        uint256 mttrMinutes
    ) external returns (uint256) {
        uint256 denom = mtbfMinutes + mttrMinutes;
        uint256 result = denom == 0 ? 0 : (mtbfMinutes * 10000) / denom;
        lastResult = result;
        emit DirectComputed("availability_mtbf_mttr_bps", result);
        return result;
    }

    function calcKwPerTonMilli(
        uint256 eerMilli
    ) external returns (uint256) {
        require(eerMilli > 0, "eer=0");
        // kW/ton = 12 / EER ; here result is scaled by 1000
        uint256 result = 12000000 / eerMilli;
        lastResult = result;
        emit DirectComputed("kw_per_ton_milli", result);
        return result;
    }

    function calcFPYBps(
        uint256 firstPassGood,
        uint256 firstPassInput
    ) external returns (uint256) {
        require(firstPassInput > 0, "input=0");
        uint256 result = (firstPassGood * 10000) / firstPassInput;
        lastResult = result;
        emit DirectComputed("fpy_bps", result);
        return result;
    }

    function calcRTY3Bps(
        uint256 fpy1Bps,
        uint256 fpy2Bps,
        uint256 fpy3Bps
    ) external returns (uint256) {
        uint256 p12 = (fpy1Bps * fpy2Bps) / 10000;
        uint256 result = (p12 * fpy3Bps) / 10000;
        lastResult = result;
        emit DirectComputed("rty3_bps", result);
        return result;
    }

    function calcSettlement(
        uint256 energyKwh,
        uint256 tariffWeiPerKwh,
        uint256 carbonKg,
        uint256 carbonWeiPerKg,
        uint256 penaltyWei
    ) external returns (uint256) {
        uint256 amount = (energyKwh * tariffWeiPerKwh) + (carbonKg * carbonWeiPerKg) + penaltyWei;
        lastResult = amount;
        emit DirectComputed("numeric_settlement", amount);
        return amount;
    }

    function evaluateQualityGate(
        uint256 defectPpm,
        uint256 vibrationMmS,
        uint256 temperatureC,
        uint256 maxDefectPpm,
        uint256 maxVibrationMmS,
        uint256 maxTemperatureC
    ) external returns (uint256) {
        bool pass = defectPpm <= maxDefectPpm &&
            vibrationMmS <= maxVibrationMmS &&
            temperatureC <= maxTemperatureC;
        uint256 result = pass ? 1 : 0;
        lastResult = result;
        emit DirectComputed("logic_quality_gate", result);
        return result;
    }

    function computeRiskScore(
        uint256 vibrationMmS,
        uint256 temperatureC,
        uint256 loadPct,
        uint256 alarmCount
    ) external returns (uint256) {
        uint256 score = (vibrationMmS * 4) + (temperatureC * 2) + loadPct + (alarmCount * 20);
        lastResult = score;
        emit DirectComputed("risk_score", score);
        return score;
    }

    function detectAnomaly(
        uint256 pressure,
        uint256 pressureRef,
        uint256 flow,
        uint256 flowRef,
        uint256 thresholdBps
    ) external returns (uint256) {
        uint256 pBps = _diffBps(pressure, pressureRef);
        uint256 fBps = _diffBps(flow, flowRef);
        uint256 total = pBps + fBps;
        uint256 result = total >= thresholdBps ? 1 : 0;
        lastResult = result;
        emit DirectComputed("logic_anomaly", result);
        return result;
    }

    // User-friendly complex optimization:
    // choose x,y,z (three plan dimensions) to minimize:
    // objective = (score(x,y,z) - targetScore)^2 + 2*(cost(x,y,z) - budget)^2
    // where:
    // score = 60*x + 25*y + 15*z
    // cost  = 400*x + 120*y + 80*z
    // search space is bounded and discretized by step.
    function computeComplexOptimization(
        uint256 targetScore,
        uint256 budget,
        uint256 step,
        uint256 xMin,
        uint256 xMax,
        uint256 yMin,
        uint256 yMax,
        uint256 zMin,
        uint256 zMax
    ) external returns (uint256) {
        require(step > 0, "invalid step");
        require(xMin <= xMax && yMin <= yMax && zMin <= zMax, "invalid bounds");

        uint256 best = type(uint256).max;

        for (uint256 x = xMin; x <= xMax; x += step) {
            for (uint256 y = yMin; y <= yMax; y += step) {
                for (uint256 z = zMin; z <= zMax; z += step) {
                    uint256 objective = _planObjective(targetScore, budget, x, y, z);
                    if (objective < best) {
                        best = objective;
                    }
                }
            }
        }

        lastResult = best;
        emit DirectComputed("complex_optimization", best);
        return best;
    }

    function _planObjective(
        uint256 targetScore,
        uint256 budget,
        uint256 x,
        uint256 y,
        uint256 z
    ) internal pure returns (uint256) {
        uint256 score = (60 * x) + (25 * y) + (15 * z);
        uint256 cost = (400 * x) + (120 * y) + (80 * z);

        uint256 scoreGap = score >= targetScore ? (score - targetScore) : (targetScore - score);
        uint256 costGap = cost >= budget ? (cost - budget) : (budget - cost);

        return (scoreGap * scoreGap) + (2 * costGap * costGap);
    }

    function computeMixedDispatchDecision(
        uint256 energyKwh,
        uint256 tariffWeiPerKwh,
        uint256 vibrationMmS,
        uint256 temperatureC,
        uint256 loadPct,
        uint256 riskThreshold,
        uint256 budgetWei
    ) external returns (uint256) {
        uint256 amount = energyKwh * tariffWeiPerKwh;
        uint256 risk = (vibrationMmS * 4) + (temperatureC * 2) + loadPct;
        uint256 decision = (amount <= budgetWei && risk <= riskThreshold) ? 1 : 0;
        lastResult = decision;
        emit DirectComputed("mixed_dispatch_decision", decision);
        return decision;
    }

    function computeMixedSettlementGuard(
        uint256 energyKwh,
        uint256 tariffWeiPerKwh,
        uint256 carbonKg,
        uint256 carbonWeiPerKg,
        uint256 defectPpm,
        uint256 maxDefectPpm,
        uint256 penaltyWei
    ) external returns (uint256) {
        uint256 amount = (energyKwh * tariffWeiPerKwh) + (carbonKg * carbonWeiPerKg);
        if (defectPpm > maxDefectPpm) {
            amount += penaltyWei;
        }
        lastResult = amount;
        emit DirectComputed("mixed_settlement_guard", amount);
        return amount;
    }

    function _diffBps(uint256 v, uint256 ref) internal pure returns (uint256) {
        uint256 denom = ref == 0 ? 1 : ref;
        uint256 diff = v >= ref ? (v - ref) : (ref - v);
        return (diff * 10000) / denom;
    }
}
