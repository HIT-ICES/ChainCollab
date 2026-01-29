package com.chaincollab.dmn.server.controller;

import com.chaincollab.dmn.server.service.DmnCacheService;
import com.chaincollab.dmn.server.service.DmnEngineService;
import com.chaincollab.dmn.server.service.DmnEngineService.InputInfo;
import org.springframework.beans.factory.annotation.Autowired;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.web3j.crypto.Hash;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.math.BigInteger;

/**
 * DMN Decision Engine API Controller
 */
@RestController
@RequestMapping("/api/dmn")
@CrossOrigin(origins = "*")
public class DmnController {

    @Autowired
    private DmnEngineService dmnEngineService;

    @Autowired
    private DmnCacheService cacheService;

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 健康检查接口
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        Map<String, Object> response = new HashMap<>();
        response.put("status", "ok");
        response.put("timestamp", System.currentTimeMillis());
        response.put("service", "DMN Decision Engine");
        response.put("version", "1.0.0");
        return ResponseEntity.ok(response);
    }

    /**
     * 执行 DMN 决策接口
     *
     * 请求体：
     * {
     *   "dmnContent": "<DMN XML 内容>",
     *   "decisionId": "决策ID",
     *   "inputData": {
     *     "变量名": 值
     *   }
     * }
     *
     * 响应：
     * {
     *   "success": true,
     *   "result": [决策结果列表],
     *   "decisionId": "决策ID",
     *   "timestamp": 时间戳
     * }
     */
    @PostMapping("/evaluate")
    public ResponseEntity<Map<String, Object>> evaluateDecision(@RequestBody Map<String, Object> request) {
        Map<String, Object> response = new HashMap<>();

        try {
            String dmnContent = (String) request.get("dmnContent");
            String decisionId = (String) request.get("decisionId");
            Map<String, Object> inputData = normalizeInputData(request.get("inputData"));

            if (dmnContent == null || decisionId == null || inputData == null) {
                response.put("success", false);
                response.put("error", "缺少必要参数：dmnContent, decisionId 或 inputData");
                return ResponseEntity.badRequest().body(response);
            }

            System.out.println("正在执行决策: " + decisionId);
            System.out.println("输入数据: " + inputData);

            // 执行决策
            List<Map<String, Object>> result = dmnEngineService.evaluateDecision(dmnContent, decisionId, inputData);

            System.out.println("决策结果: " + result);

            response.put("success", true);
            response.put("result", result);
            response.put("decisionId", decisionId);
            response.put("timestamp", System.currentTimeMillis());

            return ResponseEntity.ok(response);

        } catch (Exception e) {
            System.err.println("执行决策时出错: " + e.getMessage());
            e.printStackTrace();
            response.put("success", false);
            response.put("error", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }

    /**
     * 执行 DMN 决策并缓存结果（用于 OCR 观测）
     *
     * 请求体：
     * {
     *   "requestId": "请求ID（可选）",
     *   "dmnContent": "<DMN XML 内容>",
     *   "decisionId": "决策ID",
     *   "inputData": {...} 或 JSON 字符串
     * }
     *
     * 响应：
     * {
     *   "ok": true,
     *   "requestId": "请求ID",
     *   "value": [决策结果列表],
     *   "updatedAt": 时间戳
     * }
     */
    @PostMapping("/calc")
    public ResponseEntity<Map<String, Object>> calcAndCache(@RequestBody Map<String, Object> request) {
        Map<String, Object> response = new HashMap<>();

        try {
            String requestId = normalizeRequestId(request.get("requestId"));
            String dmnContent = (String) request.get("dmnContent");
            String decisionId = (String) request.get("decisionId");
            Map<String, Object> inputData = normalizeInputData(request.get("inputData"));

            if (dmnContent == null || decisionId == null || inputData == null) {
                response.put("ok", false);
                response.put("error", "缺少必要参数：dmnContent, decisionId 或 inputData");
                return ResponseEntity.badRequest().body(response);
            }

            List<Map<String, Object>> result = dmnEngineService.evaluateDecision(dmnContent, decisionId, inputData);
            String raw = objectMapper.writeValueAsString(result);
            String hashHex = Hash.sha3String(raw);
            BigInteger rawHash = new BigInteger(hashHex.substring(2), 16);
            BigInteger mask = BigInteger.ONE.shiftLeft(128).subtract(BigInteger.ONE);
            String hashDec = rawHash.and(mask).toString();
            DmnCacheService.CachedResult cached = cacheService.store(requestId, decisionId, result, raw, hashHex, hashDec);

            response.put("ok", true);
            response.put("requestId", requestId);
            response.put("value", result);
            response.put("updatedAt", cached.updatedAt);
            return ResponseEntity.ok(response);

        } catch (Exception e) {
            response.put("ok", false);
            response.put("error", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }

    /**
     * 获取最近一次缓存结果（用于 OCR 观测）
     */
    @GetMapping("/latest")
    public ResponseEntity<Map<String, Object>> getLatest() {
        Map<String, Object> response = new HashMap<>();
        DmnCacheService.CachedResult cached = cacheService.latest();

        if (cached == null) {
            response.put("ok", true);
            response.put("ready", false);
            response.put("value", 0);
            response.put("hashDec", 0);
            response.put("requestId", null);
            response.put("updatedAt", 0);
            return ResponseEntity.ok(response);
        }

        response.put("ok", true);
        response.put("ready", true);
        response.put("value", cached.value);
        response.put("raw", cached.raw);
        response.put("hash", cached.hashHex);
        response.put("hashDec", cached.hashDec);
        response.put("requestId", cached.requestId);
        response.put("updatedAt", cached.updatedAt);
        return ResponseEntity.ok(response);
    }

    /**
     * 按 hash 获取原始结果（用于 OCR 写回对齐）
     *
     * GET /api/dmn/by-hash?hash=...
     */
    @GetMapping("/by-hash")
    public ResponseEntity<Map<String, Object>> getByHash(@RequestParam("hash") String hash) {
        System.out.println("DMN /by-hash request hash=" + hash);
        Map<String, Object> response = new HashMap<>();
        DmnCacheService.CachedResult cached = cacheService.getByHash(hash);
        if (cached == null) {
            response.put("ok", false);
            response.put("error", "not found");
            return ResponseEntity.ok(response);
        }
        response.put("ok", true);
        response.put("raw", cached.raw);
        response.put("hash", cached.hashHex);
        response.put("hashDec", cached.hashDec);
        response.put("updatedAt", cached.updatedAt);
        return ResponseEntity.ok(response);
    }

    /**
     * OCR 写回链上后确认并清理缓存
     *
     * 请求体：
     * {
     *   "requestId": "请求ID（可选）",
     *   "aggregatorRoundId": 12,
     *   "answer": "123",
     *   "txHash": "0x...",
     *   "blockTimestampMs": 1705296340123
     * }
     *
     * 响应：
     * {
     *   "ok": true,
     *   "clearedLatest": true,
     *   "removedByRequestId": false
     * }
     */
    @PostMapping("/ack")
    public ResponseEntity<Map<String, Object>> ackAndClear(@RequestBody Map<String, Object> request) {
        String requestId = normalizeRequestId(request.get("requestId"));
        Long blockTimestampMs = normalizeLong(request.get("blockTimestampMs"));
        return ResponseEntity.ok(cacheService.ack(requestId, blockTimestampMs));
    }

    /**
     * 获取 DMN 决策信息接口
     *
     * 请求体：
     * {
     *   "dmnContent": "<DMN XML 内容>"
     * }
     *
     * 响应：
     * {
     *   "success": true,
     *   "inputs": [输入信息列表],
     *   "timestamp": 时间戳
     * }
     */
    @PostMapping("/input-info")
    public ResponseEntity<Map<String, Object>> getInputInfo(@RequestBody Map<String, Object> request) {
        Map<String, Object> response = new HashMap<>();

        try {
            String dmnContent = (String) request.get("dmnContent");

            if (dmnContent == null) {
                response.put("success", false);
                response.put("error", "缺少必要参数：dmnContent");
                return ResponseEntity.badRequest().body(response);
            }

            List<InputInfo> inputInfoList = dmnEngineService.getInputInfo(dmnContent);

            response.put("success", true);
            response.put("inputs", inputInfoList);
            response.put("timestamp", System.currentTimeMillis());

            return ResponseEntity.ok(response);

        } catch (Exception e) {
            System.err.println("获取决策信息时出错: " + e.getMessage());
            e.printStackTrace();
            response.put("success", false);
            response.put("error", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }

    /**
     * 通用异常处理
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleException(Exception e) {
        Map<String, Object> response = new HashMap<>();
        response.put("success", false);
        response.put("error", e.getMessage());
        response.put("timestamp", System.currentTimeMillis());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
    }

    private Map<String, Object> normalizeInputData(Object inputData) {
        if (inputData == null) {
            return null;
        }
        if (inputData instanceof Map) {
            return (Map<String, Object>) inputData;
        }
        if (inputData instanceof String) {
            String raw = ((String) inputData).trim();
            if (raw.isEmpty()) {
                return null;
            }
            try {
                return objectMapper.readValue(raw, new TypeReference<Map<String, Object>>() {});
            } catch (Exception e) {
                return null;
            }
        }
        return null;
    }

    private String normalizeRequestId(Object requestId) {
        if (requestId == null) {
            return null;
        }
        return String.valueOf(requestId);
    }

    private Long normalizeLong(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException e) {
            return null;
        }
    }

}
