package org.example;

import org.hyperledger.fabric.contract.annotation.DataType;
import org.hyperledger.fabric.contract.annotation.Property;

import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * @version 1.0
 * @Author 王豪
 * @Date 2024/5/17 9:33
 * @注释
 */

@DataType()
public class SampleDecisionRecord {

    //Decision information
    @Property()
    private final String DecisionInstanceID;

    //DMNInputData
    @Property()
    private final Map<String, Object> input;

    //DMNRule
    @Property()
    private final String rule;


    //DMNOutputData
    @Property()
    private final List<Map<String, Object>> output;


    public SampleDecisionRecord(String decisionInstanceID, Map<String, Object> input, String rule, List<Map<String, Object>> output) {
        DecisionInstanceID = decisionInstanceID;
        this.input = input;
        this.rule = rule;
        this.output = output;
    }

    public String getDecisionInstanceID() {
        return DecisionInstanceID;
    }

    public Map<String, Object> getInput() {
        return input;
    }

    public List<Map<String, Object>> getOutput() {
        return output;
    }

    public String getRule() {
        return rule;
    }


}
