package com.chaincollab.dmn.server.service;

import com.alibaba.fastjson.JSONObject;
import org.camunda.bpm.dmn.engine.DmnDecision;
import org.camunda.bpm.dmn.engine.DmnDecisionResult;
import org.camunda.bpm.dmn.engine.DmnEngine;
import org.camunda.bpm.dmn.engine.DmnEngineConfiguration;
import org.dom4j.Document;
import org.dom4j.DocumentException;
import org.dom4j.Element;
import org.dom4j.io.SAXReader;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * DMN Engine Service
 * 处理 DMN 决策的解析和执行
 */
@Service
public class DmnEngineService {

    private DmnEngine dmnEngine;

    @PostConstruct
    public void init() {
        // 初始化 DMN 引擎
        this.dmnEngine = DmnEngineConfiguration.createDefaultDmnEngineConfiguration().buildEngine();
        System.out.println("✅ DMN 引擎初始化成功");
    }

    /**
     * 执行 DMN 决策
     *
     * @param dmnContent DMN 模型的 XML 内容
     * @param decisionId 决策ID
     * @param inputData 输入数据
     * @return 决策结果
     */
    public List<Map<String, Object>> evaluateDecision(String dmnContent, String decisionId, Map<String, Object> inputData) {
        try (InputStream ruleInputStream = new ByteArrayInputStream(dmnContent.getBytes())) {
            // 解析 DMN 决策
            DmnDecision decision = dmnEngine.parseDecision(decisionId, ruleInputStream);

            // 执行决策
            DmnDecisionResult result = dmnEngine.evaluateDecision(decision, inputData);

            // 过滤掉包含 null 键的条目，以避免 JSON 序列化错误
            List<Map<String, Object>> filteredResult = new ArrayList<>();
            for (Map<String, Object> item : result.getResultList()) {
                Map<String, Object> filteredItem = new java.util.HashMap<>();
                for (Map.Entry<String, Object> entry : item.entrySet()) {
                    if (entry.getKey() != null && entry.getValue() != null) {
                        filteredItem.put(entry.getKey(), entry.getValue());
                    }
                }
                filteredResult.add(filteredItem);
            }
            return filteredResult;
        } catch (Exception e) {
            throw new RuntimeException("执行决策时出错: " + e.getMessage(), e);
        }
    }

    /**
     * 获取 DMN 决策的输入信息
     *
     * @param dmnContent DMN 模型的 XML 内容
     * @return 输入信息列表
     */
    public List<InputInfo> getInputInfo(String dmnContent) throws DocumentException, IOException {
        try (InputStream fis = new ByteArrayInputStream(dmnContent.getBytes())) {
            SAXReader sr = new SAXReader();
            Document doc = sr.read(fis);
            Element root = doc.getRootElement();

            List<InputInfo> dataInfoList = new ArrayList<>();
            List<String> processInputList = new ArrayList<>();

            List<Element> elementList = root.elements();
            for (Element decision : elementList) {
                // 解析所有 input
                Element decisionTable = decision.element("decisionTable");
                List<Element> inputList = decisionTable.elements("input");
                for (Element input : inputList) {
                    String id = input.attributeValue("id");
                    String label = input.attributeValue("label");
                    String type = input.element("inputExpression").attributeValue("typeRef");
                    String name = input.element("inputExpression").element("text").getText();
                    InputInfo info = new InputInfo(id, label, type, name);
                    dataInfoList.add(info);
                }

                // 解析需要剔除的过程 input
                List<Element> informationRequirementList = decision.elements("informationRequirement");
                for (Element informationRequirement : informationRequirementList) {
                    // 去掉开头的"#"
                    String processInput = informationRequirement.element("requiredDecision").attributeValue("href").substring(1);
                    processInputList.add(processInput);
                }
            }

            // 如需要，可以使用 map 降低时间复杂度
            for (String key : processInputList) {
                for (int j = 0; j < dataInfoList.size(); j++) {
                    if (key.equals(dataInfoList.get(j).getKey())) {
                        dataInfoList.remove(j);
                    }
                }
            }

            return dataInfoList;
        }
    }

    /**
     * 将 JSON 字符串转换为 Map
     */
    public Map<String, Object> parseInputData(String inputDataJson) {
        return JSONObject.parseObject(inputDataJson, Map.class);
    }

    /**
     * 输入信息类
     */
    public static class InputInfo {
        private String key;
        private String label;
        private String type;
        private String name;

        public InputInfo(String key, String label, String type, String name) {
            this.key = key;
            this.label = label;
            this.type = type;
            this.name = name;
        }

        public String getKey() {
            return key;
        }

        public void setKey(String key) {
            this.key = key;
        }

        public String getLabel() {
            return label;
        }

        public void setLabel(String label) {
            this.label = label;
        }

        public String getType() {
            return type;
        }

        public void setType(String type) {
            this.type = type;
        }

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }
    }
}
