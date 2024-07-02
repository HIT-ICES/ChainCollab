import json
import urllib.parse

import requests

xml_string = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/" xmlns:dmndi="https://www.omg.org/spec/DMN/20191111/DMNDI/" xmlns:dc="http://www.omg.org/spec/DMN/20180521/DC/" xmlns:di="http://www.omg.org/spec/DMN/20180521/DI/" xmlns:camunda="http://camunda.org/schema/1.0/dmn" id="dish" name="Dish" namespace="test-drd-2">
  <decision id="dish-decision" name="Dish Decision">
    <informationRequirement id="InformationRequirement_0vlz5d3">
      <requiredDecision href="#season" />
    </informationRequirement>
    <informationRequirement id="InformationRequirement_0n92yrg">
      <requiredDecision href="#guestCount" />
    </informationRequirement>
    <informationRequirement id="InformationRequirement_0ylxtia">
      <requiredDecision href="#season" />
    </informationRequirement>
    <informationRequirement id="InformationRequirement_0tk9qtg">
      <requiredDecision href="#guestCount" />
    </informationRequirement>
    <decisionTable id="dishDecisionTable">
      <input id="seasonInput" label="Season">
        <inputExpression id="seasonInputExpression" typeRef="string">
          <text>season</text>
        </inputExpression>
      </input>
      <input id="guestCountInput" label="How many guests">
        <inputExpression id="guestCountInputExpression" typeRef="integer">
          <text>guestCount</text>
        </inputExpression>
      </input>
      <output id="output1" label="Dish" name="desiredDish" typeRef="string" />
      <rule id="row-495762709-1">
        <inputEntry id="UnaryTests_1nxcsjr">
          <text>"Winter"</text>
        </inputEntry>
        <inputEntry id="UnaryTests_1r9yorj">
          <text>&lt;=8</text>
        </inputEntry>
        <outputEntry id="LiteralExpression_1mtwzqz">
          <text>"Spareribs"</text>
        </outputEntry>
      </rule>
      <rule id="row-495762709-2">
        <inputEntry id="UnaryTests_1lxjbif">
          <text>"Winter"</text>
        </inputEntry>
        <inputEntry id="UnaryTests_0nhiedb">
          <text>&gt;8</text>
        </inputEntry>
        <outputEntry id="LiteralExpression_1h30r12">
          <text>"Pasta"</text>
        </outputEntry>
      </rule>
      <rule id="row-495762709-3">
        <inputEntry id="UnaryTests_0ifgmfm">
          <text>"Summer"</text>
        </inputEntry>
        <inputEntry id="UnaryTests_12cib9m">
          <text>&gt;10</text>
        </inputEntry>
        <outputEntry id="LiteralExpression_0wgaegy">
          <text>"Light salad"</text>
        </outputEntry>
      </rule>
      <rule id="row-495762709-7">
        <inputEntry id="UnaryTests_0ozm9s7">
          <text>"Summer"</text>
        </inputEntry>
        <inputEntry id="UnaryTests_0sesgov">
          <text>&lt;=10</text>
        </inputEntry>
        <outputEntry id="LiteralExpression_1dvc5x3">
          <text>"Beans salad"</text>
        </outputEntry>
      </rule>
      <rule id="row-445981423-3">
        <inputEntry id="UnaryTests_1er0je1">
          <text>"Spring"</text>
        </inputEntry>
        <inputEntry id="UnaryTests_1uzqner">
          <text>&lt;10</text>
        </inputEntry>
        <outputEntry id="LiteralExpression_1pxy4g1">
          <text>"Stew"</text>
        </outputEntry>
      </rule>
      <rule id="row-445981423-4">
        <inputEntry id="UnaryTests_06or48g">
          <text>"Spring"</text>
        </inputEntry>
        <inputEntry id="UnaryTests_0wa71sy">
          <text>&gt;=10</text>
        </inputEntry>
        <outputEntry id="LiteralExpression_09ggol9">
          <text>"Steak"</text>
        </outputEntry>
      </rule>
    </decisionTable>
  </decision>
  <decision id="season" name="Season decision">
    <informationRequirement id="InformationRequirement_0tys7ju">
      <requiredInput href="#InputData_12pld2m" />
    </informationRequirement>
    <decisionTable id="seasonDecisionTable">
      <input id="temperatureInput" label="Weather in Celsius">
        <inputExpression id="temperatureInputExpression" typeRef="integer">
          <text>temperature</text>
        </inputExpression>
      </input>
      <output id="seasonOutput" label="season" name="season" typeRef="string" />
      <rule id="row-495762709-5">
        <inputEntry id="UnaryTests_1fd0eqo">
          <text>&gt;30</text>
        </inputEntry>
        <outputEntry id="LiteralExpression_0l98klb">
          <text>"Summer"</text>
        </outputEntry>
      </rule>
      <rule id="row-495762709-6">
        <inputEntry id="UnaryTests_1nz6at2">
          <text>&lt;10</text>
        </inputEntry>
        <outputEntry id="LiteralExpression_08moy1k">
          <text>"Winter"</text>
        </outputEntry>
      </rule>
      <rule id="row-445981423-2">
        <inputEntry id="UnaryTests_1a0imxy">
          <text>[10..30]</text>
        </inputEntry>
        <outputEntry id="LiteralExpression_1poftw4">
          <text>"Spring"</text>
        </outputEntry>
      </rule>
    </decisionTable>
  </decision>
  <decision id="guestCount" name="Guest Count">
    <informationRequirement id="InformationRequirement_1tdycnb">
      <requiredInput href="#InputData_1ybv19l" />
    </informationRequirement>
    <decisionTable id="guestCountDecisionTable">
      <input id="typeOfDayInput" label="Type of day">
        <inputExpression id="typeOfDayInputExpression" typeRef="string">
          <text>dayType</text>
        </inputExpression>
      </input>
      <output id="guestCountOutput" label="Guest count" name="guestCount" typeRef="integer" />
      <rule id="row-495762709-8">
        <inputEntry id="UnaryTests_0l72u8n">
          <text>"WeekDay"</text>
        </inputEntry>
        <outputEntry id="LiteralExpression_0wuwqaz">
          <text>4</text>
        </outputEntry>
      </rule>
      <rule id="row-495762709-9">
        <inputEntry id="UnaryTests_03a73o9">
          <text>"Holiday"</text>
        </inputEntry>
        <outputEntry id="LiteralExpression_1whn119">
          <text>10</text>
        </outputEntry>
      </rule>
      <rule id="row-495762709-10">
        <inputEntry id="UnaryTests_12tygwt">
          <text>"Weekend"</text>
        </inputEntry>
        <outputEntry id="LiteralExpression_1b5k9t8">
          <text>15</text>
        </outputEntry>
      </rule>
    </decisionTable>
  </decision>
  <inputData id="InputData_12pld2m" name="temperature" />
  <inputData id="InputData_1ybv19l" name="dayType" />
  <dmndi:DMNDI>
    <dmndi:DMNDiagram id="DMNDiagram_0zqvrkc">
      <dmndi:DMNShape id="DMNShape_085mwzu" dmnElementRef="dish-decision">
        <dc:Bounds height="80" width="180" x="420" y="60" />
      </dmndi:DMNShape>
      <dmndi:DMNShape id="DMNShape_1fbh9l9" dmnElementRef="season">
        <dc:Bounds height="80" width="180" x="130" y="260" />
      </dmndi:DMNShape>
      <dmndi:DMNShape id="DMNShape_1lwjonf" dmnElementRef="guestCount">
        <dc:Bounds height="80" width="180" x="720" y="280" />
      </dmndi:DMNShape>
      <dmndi:DMNEdge id="DMNEdge_1t5agin" dmnElementRef="InformationRequirement_0ylxtia">
        <di:waypoint x="220" y="260" />
        <di:waypoint x="480" y="160" />
        <di:waypoint x="480" y="140" />
      </dmndi:DMNEdge>
      <dmndi:DMNEdge id="DMNEdge_0rs98c6" dmnElementRef="InformationRequirement_0tk9qtg">
        <di:waypoint x="810" y="280" />
        <di:waypoint x="540" y="160" />
        <di:waypoint x="540" y="140" />
      </dmndi:DMNEdge>
      <dmndi:DMNShape id="DMNShape_1l1qoeo" dmnElementRef="InputData_12pld2m">
        <dc:Bounds height="45" width="125" x="157" y="477" />
      </dmndi:DMNShape>
      <dmndi:DMNEdge id="DMNEdge_0tnxv4l" dmnElementRef="InformationRequirement_0tys7ju">
        <di:waypoint x="220" y="477" />
        <di:waypoint x="220" y="360" />
        <di:waypoint x="220" y="340" />
      </dmndi:DMNEdge>
      <dmndi:DMNShape id="DMNShape_14l4bbp" dmnElementRef="InputData_1ybv19l">
        <dc:Bounds height="45" width="125" x="757" y="517" />
      </dmndi:DMNShape>
      <dmndi:DMNEdge id="DMNEdge_1ar7p5v" dmnElementRef="InformationRequirement_1tdycnb">
        <di:waypoint x="820" y="517" />
        <di:waypoint x="810" y="380" />
        <di:waypoint x="810" y="360" />
      </dmndi:DMNEdge>
    </dmndi:DMNDiagram>
  </dmndi:DMNDI>
</definitions>

"""


def encode_decode_xml_string(xml_string):
    encoded_xml_string = urllib.parse.quote(xml_string)

    print(encoded_xml_string)
    print("\n\n")
    # 解码字符串
    decoded_str = urllib.parse.unquote(encoded_xml_string)

    print(decoded_str)

    print(decoded_str == xml_string)


def invoke_chaincode():
    # 目标URL
    url = "http://127.0.0.1:5000/api/v1/namespaces/default/apis/Test5/invoke/CreateInstance"

    parameters = {
        "Participant_1080bkg": {
            "msp": "Mem.org.comMSP",
            "attributes": {},
            "isMulti": False,
            "multiMaximum": 0,
            "multiMinimum": 0,
            "x509": "",
        },
        "Participant_0sktaei": {
            "msp": "Org1-con.org.comMSP",
            "attributes": {},
            "isMulti": False,
            "multiMaximum": 0,
            "multiMinimum": 0,
            "x509": "",
        },
        "Participant_1gcdqza": {
            "msp": "Org1-con.org.comMSP",
            "attributes": {},
            "isMulti": False,
            "multiMaximum": 0,
            "multiMinimum": 0,
            "x509": "",
        },
        "Activity_0ysk2q6": {
            "cid": "",
            "hash": "",
            "decisionId": "dish-decision",
            "mapping": {"temperature": "temperature", "dayType": "dataType"},
            "state": 0,
        },
        "Activity_0ysk2q6_Content": "",
        # "Activity_0ysk2q6_Content": xml_string,
    }

    # JSON请求体
    request_body = {"input": {"initParametersBytes": json.dumps(parameters)}}
    print("initParametersBytes: ", json.dumps(parameters))
    # 将JSON请求体转为字符串
    json_data = json.dumps(request_body)

    # Headers
    headers = {
        "Content-Type": "application/json",
    }

    # 发送POST请求
    response = requests.post(url, data=json_data, headers=headers)

    # 打印响应
    print(response.status_code)
    print(response.text)


# encode_decode_xml_string(xml_string)
invoke_chaincode()
