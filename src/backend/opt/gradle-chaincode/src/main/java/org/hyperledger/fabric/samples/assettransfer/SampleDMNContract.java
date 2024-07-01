package org.example;

import com.alibaba.fastjson.JSONObject;
import com.owlike.genson.Genson;
import org.apache.commons.io.IOUtils;
import org.camunda.bpm.dmn.engine.DmnDecision;
import org.camunda.bpm.dmn.engine.DmnDecisionResult;
import org.camunda.bpm.dmn.engine.DmnEngine;
import org.camunda.bpm.dmn.engine.DmnEngineConfiguration;
import org.dom4j.Document;
import org.dom4j.DocumentException;
import org.dom4j.Element;
import org.dom4j.io.SAXReader;
import org.hyperledger.fabric.contract.Context;
import org.hyperledger.fabric.contract.ContractInterface;
import org.hyperledger.fabric.contract.annotation.*;
import org.hyperledger.fabric.shim.ChaincodeStub;
import org.hyperledger.fabric.shim.ChaincodeBase;


import java.io.*;
import java.util.List;
import java.util.Map;
import java.util.ArrayList;

/**
 * @version 1.0
 * @Author 王豪
 * @Date 2024/5/17 10:01
 * @注释
 */

@Contract(
        name = "basic",
        info = @Info(
                title = "SampleDMNContract",
                description = "none",
                version = "0.0.1-SNAPSHOT",
                license = @License(
                        name = "Apache 2.0 License",
                        url = "http://www.apache.org/licenses/LICENSE-2.0.html"),
                contact = @Contact(
                        email = "aaa@example.com",
                        name = "aaa",
                        url = "aaa")))
@Default
public final class SampleDMNContract implements ContractInterface{
    private final Genson genson = new Genson();
    private final DmnEngine dmnEngine = DmnEngineConfiguration.createDefaultDmnEngineConfiguration().buildEngine();

    public SampleDMNContract(){

    }
    
    /**
     * 决策逻辑，引入决策引擎处理
     */
    private List<Map<String, Object>> Decide(Map<String, Object> data, InputStream ruleInputStream,String decisionId){
        DmnDecision decision = dmnEngine.parseDecision(decisionId,ruleInputStream);
        DmnDecisionResult result = dmnEngine.evaluateDecision(decision, data);
        return result.getResultList();
    }


    /**
     * 获取InputData部分
     *     1.json字符串（简易实现，只能识别数字和字符串）
     */
    private Map<String, Object> getInputDataByJSON(String inputDataJson){
        return JSONObject.parseObject(inputDataJson,Map.class);
    }

    /**
     * 获取InputData部分
     *     2.json字符串（所有类型的实现，包括Date等）TODO
     */
    private Map<String, Object> getInputDataByJSONAllType(String inputDataJson){

        List JSONObjectList = JSONObject.parseObject(inputDataJson,List.class);

        //这里写对List<jsonobject>中的每个对象（含type,key,value）进行解析的逻辑

        return null;
    }

    /**
     * 获取InputInfo部分
     *     1.通过本地xml文件
     *     TODO: 2.通过链上xml文件
     */
    public List<InputInfo> GetInputInfoByDMNFile(String dmnContent) throws DocumentException, IOException {
        // Dmn dmn = queryDMN(stub,dmnKey);
        // String dmnFileString = dmn.getDmnContent();
        InputStream fis = new ByteArrayInputStream(dmnContent.getBytes());
        // FileInputStream fis = new FileInputStream(filePath1);
        SAXReader sr = new SAXReader();
        Document doc = sr.read(fis);
        Element root = doc.getRootElement();

        List<InputInfo> DataInfoList = new ArrayList<>();
        List<String> processInputList = new ArrayList<>();

        List<Element> elementList = root.elements();
        for (Element decision : elementList) {
            //解析所有input
            Element decisionTable = decision.element("decisionTable");
            List<Element> inputList = decisionTable.elements("input");
            for (Element input : inputList) {
                String id = input.attributeValue("id");
                String label = input.attributeValue("label");
                String type = input.element("inputExpression").attributeValue("typeRef");
                String name = input.element("inputExpression").element("text").getText();
                InputInfo info = new InputInfo(id, label, type, name);
                DataInfoList.add(info);
            }

            //解析需要剔除的过程input
            List<Element> informationRequirementList = decision.elements("informationRequirement");
            for (Element informationRequirement : informationRequirementList) {
                //去掉开头的"#"
                String processInput = informationRequirement.element("requiredDecision").attributeValue("href").substring(1);
                processInputList.add(processInput);
            }
        }
        //如需要，可以使用map降低时间复杂度
        for (String key : processInputList) {
            for (int j = 0; j < DataInfoList.size(); j++) {
                if (key.equals(DataInfoList.get(j).getKey())) DataInfoList.remove(j);
            }
        }
        fis.close();

        return DataInfoList;
    }

//  /**
//      * 获取InputInfo部分
//      *     1.通过本地xml文件
//      *     TODO: 2.通过链上xml文件
//      */
//     public List<InputInfo> GetInputInfoByDMNFile(String filePath1) throws DocumentException, IOException {
//         FileInputStream fis = new FileInputStream(filePath1);
//         SAXReader sr = new SAXReader();
//         Document doc = sr.read(fis);
//         Element root = doc.getRootElement();

//         List<InputInfo> DataInfoList = new ArrayList<>();
//         List<String> processInputList = new ArrayList<>();

//         List<Element> elementList = root.elements();
//         for (Element decision : elementList) {
//             //解析所有input
//             Element decisionTable = decision.element("decisionTable");
//             List<Element> inputList = decisionTable.elements("input");
//             for (Element input : inputList) {
//                 String id = input.attributeValue("id");
//                 String label = input.attributeValue("label");
//                 String type = input.element("inputExpression").attributeValue("typeRef");
//                 String name = input.element("inputExpression").element("text").getText();
//                 InputInfo info = new InputInfo(id, label, type, name);
//                 DataInfoList.add(info);
//             }

//             //解析需要剔除的过程input
//             List<Element> informationRequirementList = decision.elements("informationRequirement");
//             for (Element informationRequirement : informationRequirementList) {
//                 //去掉开头的"#"
//                 String processInput = informationRequirement.element("requiredDecision").attributeValue("href").substring(1);
//                 processInputList.add(processInput);
//             }
//         }
//         //如需要，可以使用map降低时间复杂度
//         for (String key : processInputList) {
//             for (int j = 0; j < DataInfoList.size(); j++) {
//                 if (key.equals(DataInfoList.get(j).getKey())) DataInfoList.remove(j);
//             }
//         }
//         fis.close();

//         return DataInfoList;
//     }

    /**
     * record上链
     */
    @Transaction(intent = Transaction.TYPE.SUBMIT)
    public SampleDecisionRecord createRecord(Context ctx, String inputDataJson, String dmnContent, String decisionId) throws IOException {
        ChaincodeStub stub = ctx.getStub();

        //模拟Data输入
        Map<String, Object> input = getInputDataByJSON(inputDataJson);
        // Map<String, Object> input = GetInputDataByJSONAllType(inputDataJson);

        //模拟rule输入和决策
        // Dmn dmn = queryDMN(stub,dmnKeyId);
        // String dmnContent = dmn.getDmnContent();
        InputStream inputStreamRule = new ByteArrayInputStream(dmnContent.getBytes());
        List<Map<String, Object>> output = Decide(input,inputStreamRule,decisionId);

        //record其他信息
        SampleDecisionRecord record= new SampleDecisionRecord(decisionId,input,dmnContent,output);


        String sortedJson = genson.serialize(record);
        stub.putStringState(decisionId, sortedJson);
        return record;
    }

    public static void main(String[] args) {
        //{key,value,type}
        // type : dmnType
        String inputDataJson = "{\"temperature\":20,\"dayType\":\"WeekDay\"}";
        String dmnKeyId = "drdDish";
        String decisionId = "dish-decision";
        // new SampleDMNContract().createRecord("decisionId", inputDataJson, dmnKeyId, decisionId);
    }
}