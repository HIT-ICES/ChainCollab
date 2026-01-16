package com.chaincollab.dmn.server.controller;

import com.chaincollab.dmn.server.service.DmnEngineService;
import com.chaincollab.dmn.server.service.DmnEngineService.InputInfo;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * DMN Decision Engine API Controller
 */
@RestController
@RequestMapping("/api/dmn")
@CrossOrigin(origins = "*")
public class DmnController {

    @Autowired
    private DmnEngineService dmnEngineService;

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
            Map<String, Object> inputData = (Map<String, Object>) request.get("inputData");

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
}
