package org.example;

/**
 * @version 1.0
 * @Author 王豪
 * @Date 2024/5/23 15:04
 * @注释
 */

public final class InputInfo {
    private final String inputID;

    private final String labelName;
    private final String dataType;
    private final String key;


    public InputInfo(String inputID, String labelName, String dataType, String key) {
        this.inputID = inputID;
        this.labelName = labelName;
        this.dataType = dataType;
        this.key = key;
    }

    public String getInputID() {
        return inputID;
    }

    public String getLabelName() {
        return labelName;
    }

    public String getDataType() {
        return dataType;
    }

    public String getKey() {
        return key;
    }

    @Override
    public String toString() {
        return "InputInfo{" +
                "inputID='" + inputID + '\'' +
                ", labelName='" + labelName + '\'' +
                ", dataType='" + dataType + '\'' +
                ", key='" + key + '\'' +
                '}';
    }
}
