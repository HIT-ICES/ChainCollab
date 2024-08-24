import os
import sys
import json
import argparse

import requests

from invoker import extract_url_port, invoke_task
from noise_generator import generate_random_path, RandomMode
from loader import step_loader, Task


def get_parser():
    parser = argparse.ArgumentParser(description="This is the help message")

    subparsers = parser.add_subparsers(dest="command")

    # Help command
    parser_help = subparsers.add_parser(
        "help", aliases=["-h", "--help"], help="Print this help message"
    )

    # Run command
    parser_run = subparsers.add_parser(
        "run", aliases=["-r", "--run"], help="Run an experiment"
    )
    parser_run.add_argument("-input", help="Input file name", required=True)
    parser_run.add_argument("-output", help="Output file name", default="output.json")
    parser_run.add_argument("-e", help="append path only mode", action="store_true", default=False)
    parser_run.add_argument(
        "-n", type=int, help="Number of noise to generate", default=1
    )
    parser_run.add_argument(
        "-N", type=int, help="Number of path to generate", default=1
    )
    parser_run.add_argument(
        "-m",
        help="Mode of noise generation, like ars ar as etc. add|remove|switch including add, remove, and switch, default is all, -t ars",
        default="ars",
    )
    parser_run.add_argument(
        "-listen",
        help="Create listener and subscribe to the contract event",
        action="store_true",
    )
    return parser


def default_response():
    print("Invalid command. Use -h or --help for help.")


def run_experiment(
    task,
    random_mode,
    random_num=1,
    experiment_num=1,
    create_listener=False,
):
    def create_listener_and_subscribe(
        event_name: str, contract_name, url: str, contract_interface_id: str
    ):
        firefly_url, firefly_port = extract_url_port(url)
        res = requests.post(
            f"{firefly_url}:{firefly_port}/api/v1/namespaces/default/contracts/listeners",
            json={
                "interface": {"id": contract_interface_id},
                "location": {"channel": "default", "chaincode": contract_name},
                "event": {"name": event_name},
                "options": {"firstEvent": "oldest"},
                "topic": event_name + "-" + contract_name,
            },
            # headers={
            #     "Content-Type": "application/json",
            # },
        )
        print("Create listener ", res.json())
        listener_id = res.json()["id"]
        res = requests.post(
            f"{firefly_url}:{firefly_port}/api/v1/namespaces/default/subscriptions",
            json={
                "namespace": "default",
                "name": event_name + "-" + contract_name,
                "transport": "websockets",
                "filter": {
                    "events": "blockchain_event_received",
                    "blockchainevent": {"listener": listener_id},
                },
                "options": {"firstEvent": "oldest"},
            },
            headers={
                "Content-Type": "application/json",
            },
        )
        print("Subscribe ", res.json())

    # generate
    execute_paths = [list(range(len(task.invoke_path)))]
    while len(execute_paths) <= experiment_num:
        random_path = generate_random_path(task.invoke_path, random_mode, random_num)
        if random_path not in execute_paths:
            execute_paths.append(random_path)
    execute_paths.extend(task.appended_index_paths)
    # execute and output
    results = []

    # copy params here!!!!
    # param = """{"Participant_1080bkg":{"msp":"Testmembership-2.org.comMSP","attributes":{},"isMulti":false,"multiMaximum":0,"multiMinimum":0,"x509":"eDUwOTo6Q049bWVtYmVyMSxPVT1jbGllbnQ6OkNOPWNhLnRlc3RNZW1iZXJzaGlwLTIub3JnLmNvbSxPVT1GYWJyaWMsTz10ZXN0TWVtYmVyc2hpcC0yLm9yZy5jb20sU1Q9Tm9ydGggQ2Fyb2xpbmEsQz1VUw==@Testmembership-2.org.comMSP"},"Participant_1gcdqza":{"msp":"Testorg-testconsortium.org.comMSP","attributes":{},"isMulti":false,"multiMaximum":0,"multiMinimum":0,"x509":"eDUwOTo6Q049dGVzdE1lbWJlcixPVT1jbGllbnQ6OkNOPWNhLnRlc3RPcmctdGVzdENvbnNvcnRpdW0ub3JnLmNvbSxPVT1GYWJyaWMsTz10ZXN0T3JnLXRlc3RDb25zb3J0aXVtLm9yZy5jb20sU1Q9Tm9ydGggQ2Fyb2xpbmEsQz1VUw==@Testorg-testconsortium.org.comMSP"},"Participant_0sktaei":{"msp":"Testmembership-1.org.comMSP","attributes":{},"isMulti":false,"multiMaximum":0,"multiMinimum":0,"x509":"eDUwOTo6Q049bWVtYmVyMixPVT1jbGllbnQ6OkNOPWNhLnRlc3RNZW1iZXJzaGlwLTEub3JnLmNvbSxPVT1GYWJyaWMsTz10ZXN0TWVtYmVyc2hpcC0xLm9yZy5jb20sU1Q9Tm9ydGggQ2Fyb2xpbmEsQz1VUw==@Testmembership-1.org.comMSP"},"Activity_1yl9tfp_DecisionID":"decision_0tybghz","Activity_1yl9tfp_ParamMapping":{"VIPpoints":"VIPpoints","need_external_provider":"need_external_provider","externalAvailable":"externalAvailable"},"Activity_1yl9tfp_Content":"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<definitions xmlns=\"https://www.omg.org/spec/DMN/20191111/MODEL/\" xmlns:biodi=\"http://bpmn.io/schema/dmn/biodi/2.0\" xmlns:dmndi=\"https://www.omg.org/spec/DMN/20191111/DMNDI/\" xmlns:dc=\"http://www.omg.org/spec/DMN/20180521/DC/\" xmlns:di=\"http://www.omg.org/spec/DMN/20180521/DI/\" id=\"definitions_1olsuce\" name=\"definitions\" namespace=\"http://camunda.org/schema/1.0/dmn\" exporter=\"Camunda Modeler\" exporterVersion=\"5.22.0\">\n  <decision id=\"decision_0tybghz\" name=\"customer1\">\n    <informationRequirement id=\"InformationRequirement_1hoht1b\">\n      <requiredInput href=\"#InputData_1g61x6h\" />\n    </informationRequirement>\n    <informationRequirement id=\"InformationRequirement_0h8ttmr\">\n      <requiredInput href=\"#InputData_04naupt\" />\n    </informationRequirement>\n    <decisionTable id=\"decisionTable_1v3tii8\" hitPolicy=\"FIRST\">\n      <input id=\"input1\" label=\"VIPpoints\" biodi:width=\"192\">\n        <inputExpression id=\"inputExpression1\" typeRef=\"number\">\n          <text>VIPpoints</text>\n        </inputExpression>\n      </input>\n      <input id=\"InputClause_1i7xu16\" label=\"need_external_provider\" biodi:width=\"192\">\n        <inputExpression id=\"LiteralExpression_1hd5g8t\" typeRef=\"boolean\">\n          <text>need_external_provider</text>\n        </inputExpression>\n      </input>\n      <output id=\"output1\" label=\"externalAvailable\" name=\"externalAvailable\" typeRef=\"boolean\" />\n      <rule id=\"DecisionRule_0cs4468\">\n        <inputEntry id=\"UnaryTests_1aut0oo\">\n          <text>&lt;=9999</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0lq0fko\">\n          <text></text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_11etaq9\">\n          <text>false</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_1vbhylp\">\n        <inputEntry id=\"UnaryTests_17t02el\">\n          <text></text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_1ik5kui\">\n          <text>false</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_1amyrv5\">\n          <text>false</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_1l5kdzl\">\n        <inputEntry id=\"UnaryTests_0d8927n\">\n          <text>&gt;=10000</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0bqww61\">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_0z0fcvd\">\n          <text>true</text>\n        </outputEntry>\n      </rule>\n    </decisionTable>\n  </decision>\n  <inputData id=\"InputData_1g61x6h\" name=\"VIPpoints\" />\n  <inputData id=\"InputData_04naupt\" name=\"need_external_provider\" />\n  <dmndi:DMNDI>\n    <dmndi:DMNDiagram id=\"DMNDiagram_1flr508\">\n      <dmndi:DMNShape id=\"DMNShape_0fg1a7g\" dmnElementRef=\"decision_0tybghz\">\n        <dc:Bounds height=\"80\" width=\"180\" x=\"460\" y=\"70\" />\n      </dmndi:DMNShape>\n      <dmndi:DMNShape id=\"DMNShape_0g5yhqk\" dmnElementRef=\"InputData_1g61x6h\">\n        <dc:Bounds height=\"45\" width=\"125\" x=\"258\" y=\"238\" />\n      </dmndi:DMNShape>\n      <dmndi:DMNShape id=\"DMNShape_1inp6do\" dmnElementRef=\"InputData_04naupt\">\n        <dc:Bounds height=\"45\" width=\"125\" x=\"678\" y=\"258\" />\n      </dmndi:DMNShape>\n      <dmndi:DMNEdge id=\"DMNEdge_06eiibn\" dmnElementRef=\"InformationRequirement_1hoht1b\">\n        <di:waypoint x=\"321\" y=\"238\" />\n        <di:waypoint x=\"520\" y=\"170\" />\n        <di:waypoint x=\"520\" y=\"150\" />\n      </dmndi:DMNEdge>\n      <dmndi:DMNEdge id=\"DMNEdge_1qs00fv\" dmnElementRef=\"InformationRequirement_0h8ttmr\">\n        <di:waypoint x=\"741\" y=\"258\" />\n        <di:waypoint x=\"580\" y=\"170\" />\n        <di:waypoint x=\"580\" y=\"150\" />\n      </dmndi:DMNEdge>\n    </dmndi:DMNDiagram>\n  </dmndi:DMNDI>\n</definitions>\n","Activity_0ibsbry_DecisionID":"decision_0tybghz","Activity_0ibsbry_ParamMapping":{"invoiceType":"invoiceType","invoice":"invoice","invoiceTypeAvailable":"invoiceAvailable"},"Activity_0ibsbry_Content":"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<definitions xmlns=\"https://www.omg.org/spec/DMN/20191111/MODEL/\" xmlns:biodi=\"http://bpmn.io/schema/dmn/biodi/2.0\" xmlns:dmndi=\"https://www.omg.org/spec/DMN/20191111/DMNDI/\" xmlns:dc=\"http://www.omg.org/spec/DMN/20180521/DC/\" id=\"definitions_1olsuce\" name=\"definitions\" namespace=\"http://camunda.org/schema/1.0/dmn\" exporter=\"Camunda Modeler\" exporterVersion=\"5.22.0\">\n  <decision id=\"decision_0tybghz\" name=\"customer2\">\n    <decisionTable id=\"decisionTable_1v3tii8\" hitPolicy=\"FIRST\">\n      <input id=\"input1\" label=\"invoiceType\" biodi:width=\"192\">\n        <inputExpression id=\"inputExpression1\" typeRef=\"string\">\n          <text>invoiceType</text>\n        </inputExpression>\n      </input>\n      <input id=\"InputClause_02k362l\" label=\"invoice\">\n        <inputExpression id=\"LiteralExpression_1uexm9z\" typeRef=\"boolean\">\n          <text>invoice</text>\n        </inputExpression>\n      </input>\n      <output id=\"output1\" label=\"invoiceTypeAvailable\" name=\"invoiceTypeAvailable\" typeRef=\"boolean\" biodi:width=\"192\" />\n      <rule id=\"DecisionRule_1oyddrr\">\n        <inputEntry id=\"UnaryTests_1wvkvfa\">\n          <text>\"HIT\"</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0xgibym\">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_1esf1bm\">\n          <text>true</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_0f5g2m7\">\n        <inputEntry id=\"UnaryTests_069nkt8\">\n          <text>\"HITwh\"</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0m8uhu2\">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_0cm8blh\">\n          <text>true</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_0bo63a3\">\n        <inputEntry id=\"UnaryTests_1dkdmmv\">\n          <text></text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_086c8ll\">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_0rhhni5\">\n          <text>false</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_1wdnie7\">\n        <inputEntry id=\"UnaryTests_0t432ic\">\n          <text></text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0yb6s1z\">\n          <text>false</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_14n15xx\">\n          <text>false</text>\n        </outputEntry>\n      </rule>\n    </decisionTable>\n  </decision>\n  <dmndi:DMNDI>\n    <dmndi:DMNDiagram id=\"DMNDiagram_19nwh5y\">\n      <dmndi:DMNShape id=\"DMNShape_03xv25j\" dmnElementRef=\"decision_0tybghz\">\n        <dc:Bounds height=\"80\" width=\"180\" x=\"150\" y=\"80\" />\n      </dmndi:DMNShape>\n    </dmndi:DMNDiagram>\n  </dmndi:DMNDI>\n</definitions>\n"}"""
    param = {
        "Participant_0sktaei": {
            "msp": "Testmembership-1.org.comMSP",
            "attributes": {},
            "isMulti": False,
            "multiMaximum": 0,
            "multiMinimum": 0,
            "x509": "eDUwOTo6Q049dXNlcjIsT1U9Y2xpZW50OjpDTj1jYS50ZXN0TWVtYmVyc2hpcC0xLm9yZy5jb20sT1U9RmFicmljLE89dGVzdE1lbWJlcnNoaXAtMS5vcmcuY29tLFNUPU5vcnRoIENhcm9saW5hLEM9VVM=@Testmembership-1.org.comMSP",
        },
        "Participant_1080bkg": {
            "msp": "Testmembership-2.org.comMSP",
            "attributes": {},
            "isMulti": False,
            "multiMaximum": 0,
            "multiMinimum": 0,
            "x509": "eDUwOTo6Q049dXNlcjEsT1U9Y2xpZW50OjpDTj1jYS50ZXN0TWVtYmVyc2hpcC0yLm9yZy5jb20sT1U9RmFicmljLE89dGVzdE1lbWJlcnNoaXAtMi5vcmcuY29tLFNUPU5vcnRoIENhcm9saW5hLEM9VVM=@Testmembership-2.org.comMSP",
        },
        "Participant_1gcdqza": {
            "msp": "Testorg-testconsortium.org.comMSP",
            "attributes": {},
            "isMulti": False,
            "multiMaximum": 0,
            "multiMinimum": 0,
            "x509": "eDUwOTo6Q049dXNlcjMsT1U9Y2xpZW50OjpDTj1jYS50ZXN0T3JnLXRlc3RDb25zb3J0aXVtLm9yZy5jb20sT1U9RmFicmljLE89dGVzdE9yZy10ZXN0Q29uc29ydGl1bS5vcmcuY29tLFNUPU5vcnRoIENhcm9saW5hLEM9VVM=@Testorg-testconsortium.org.comMSP",
        },
        "Activity_1yl9tfp_DecisionID": "decision_0tybghz",
        "Activity_1yl9tfp_ParamMapping": {
            "VIPpoints": "VIPpoints",
            "need_external_provider": "need_external_provider",
            "externalAvailable": "externalAvailable",
        },
        "Activity_1yl9tfp_Content": '<?xml version="1.0" encoding="UTF-8"?>\n<definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/" xmlns:biodi="http://bpmn.io/schema/dmn/biodi/2.0" xmlns:dmndi="https://www.omg.org/spec/DMN/20191111/DMNDI/" xmlns:dc="http://www.omg.org/spec/DMN/20180521/DC/" xmlns:di="http://www.omg.org/spec/DMN/20180521/DI/" id="definitions_1olsuce" name="definitions" namespace="http://camunda.org/schema/1.0/dmn" exporter="Camunda Modeler" exporterVersion="5.22.0">\n  <decision id="decision_0tybghz" name="customer1">\n    <informationRequirement id="InformationRequirement_1hoht1b">\n      <requiredInput href="#InputData_1g61x6h" />\n    </informationRequirement>\n    <informationRequirement id="InformationRequirement_0h8ttmr">\n      <requiredInput href="#InputData_04naupt" />\n    </informationRequirement>\n    <decisionTable id="decisionTable_1v3tii8" hitPolicy="FIRST">\n      <input id="input1" label="VIPpoints" biodi:width="192">\n        <inputExpression id="inputExpression1" typeRef="number">\n          <text>VIPpoints</text>\n        </inputExpression>\n      </input>\n      <input id="InputClause_1i7xu16" label="need_external_provider" biodi:width="192">\n        <inputExpression id="LiteralExpression_1hd5g8t" typeRef="boolean">\n          <text>need_external_provider</text>\n        </inputExpression>\n      </input>\n      <output id="output1" label="externalAvailable" name="externalAvailable" typeRef="boolean" />\n      <rule id="DecisionRule_0cs4468">\n        <inputEntry id="UnaryTests_1aut0oo">\n          <text>&lt;=9999</text>\n        </inputEntry>\n        <inputEntry id="UnaryTests_0lq0fko">\n          <text></text>\n        </inputEntry>\n        <outputEntry id="LiteralExpression_11etaq9">\n          <text>false</text>\n        </outputEntry>\n      </rule>\n      <rule id="DecisionRule_1vbhylp">\n        <inputEntry id="UnaryTests_17t02el">\n          <text></text>\n        </inputEntry>\n        <inputEntry id="UnaryTests_1ik5kui">\n          <text>false</text>\n        </inputEntry>\n        <outputEntry id="LiteralExpression_1amyrv5">\n          <text>false</text>\n        </outputEntry>\n      </rule>\n      <rule id="DecisionRule_1l5kdzl">\n        <inputEntry id="UnaryTests_0d8927n">\n          <text>&gt;=10000</text>\n        </inputEntry>\n        <inputEntry id="UnaryTests_0bqww61">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id="LiteralExpression_0z0fcvd">\n          <text>true</text>\n        </outputEntry>\n      </rule>\n    </decisionTable>\n  </decision>\n  <inputData id="InputData_1g61x6h" name="VIPpoints" />\n  <inputData id="InputData_04naupt" name="need_external_provider" />\n  <dmndi:DMNDI>\n    <dmndi:DMNDiagram id="DMNDiagram_1flr508">\n      <dmndi:DMNShape id="DMNShape_0fg1a7g" dmnElementRef="decision_0tybghz">\n        <dc:Bounds height="80" width="180" x="460" y="70" />\n      </dmndi:DMNShape>\n      <dmndi:DMNShape id="DMNShape_0g5yhqk" dmnElementRef="InputData_1g61x6h">\n        <dc:Bounds height="45" width="125" x="258" y="238" />\n      </dmndi:DMNShape>\n      <dmndi:DMNShape id="DMNShape_1inp6do" dmnElementRef="InputData_04naupt">\n        <dc:Bounds height="45" width="125" x="678" y="258" />\n      </dmndi:DMNShape>\n      <dmndi:DMNEdge id="DMNEdge_06eiibn" dmnElementRef="InformationRequirement_1hoht1b">\n        <di:waypoint x="321" y="238" />\n        <di:waypoint x="520" y="170" />\n        <di:waypoint x="520" y="150" />\n      </dmndi:DMNEdge>\n      <dmndi:DMNEdge id="DMNEdge_1qs00fv" dmnElementRef="InformationRequirement_0h8ttmr">\n        <di:waypoint x="741" y="258" />\n        <di:waypoint x="580" y="170" />\n        <di:waypoint x="580" y="150" />\n      </dmndi:DMNEdge>\n    </dmndi:DMNDiagram>\n  </dmndi:DMNDI>\n</definitions>\n',
        "Activity_0ibsbry_DecisionID": "decision_0tybghz",
        "Activity_0ibsbry_ParamMapping": {
            "invoiceType": "invoiceType",
            "invoice": "invoice",
            "invoiceTypeAvailable": "invoiceAvailable",
        },
        "Activity_0ibsbry_Content": '<?xml version="1.0" encoding="UTF-8"?>\n<definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/" xmlns:biodi="http://bpmn.io/schema/dmn/biodi/2.0" xmlns:dmndi="https://www.omg.org/spec/DMN/20191111/DMNDI/" xmlns:dc="http://www.omg.org/spec/DMN/20180521/DC/" id="definitions_1olsuce" name="definitions" namespace="http://camunda.org/schema/1.0/dmn" exporter="Camunda Modeler" exporterVersion="5.22.0">\n  <decision id="decision_0tybghz" name="customer2">\n    <decisionTable id="decisionTable_1v3tii8" hitPolicy="FIRST">\n      <input id="input1" label="invoiceType" biodi:width="192">\n        <inputExpression id="inputExpression1" typeRef="string">\n          <text>invoiceType</text>\n        </inputExpression>\n      </input>\n      <input id="InputClause_02k362l" label="invoice">\n        <inputExpression id="LiteralExpression_1uexm9z" typeRef="boolean">\n          <text>invoice</text>\n        </inputExpression>\n      </input>\n      <output id="output1" label="invoiceTypeAvailable" name="invoiceTypeAvailable" typeRef="boolean" biodi:width="192" />\n      <rule id="DecisionRule_1oyddrr">\n        <inputEntry id="UnaryTests_1wvkvfa">\n          <text>"HIT"</text>\n        </inputEntry>\n        <inputEntry id="UnaryTests_0xgibym">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id="LiteralExpression_1esf1bm">\n          <text>true</text>\n        </outputEntry>\n      </rule>\n      <rule id="DecisionRule_0f5g2m7">\n        <inputEntry id="UnaryTests_069nkt8">\n          <text>"HITwh"</text>\n        </inputEntry>\n        <inputEntry id="UnaryTests_0m8uhu2">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id="LiteralExpression_0cm8blh">\n          <text>true</text>\n        </outputEntry>\n      </rule>\n      <rule id="DecisionRule_0bo63a3">\n        <inputEntry id="UnaryTests_1dkdmmv">\n          <text></text>\n        </inputEntry>\n        <inputEntry id="UnaryTests_086c8ll">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id="LiteralExpression_0rhhni5">\n          <text>false</text>\n        </outputEntry>\n      </rule>\n      <rule id="DecisionRule_1wdnie7">\n        <inputEntry id="UnaryTests_0t432ic">\n          <text></text>\n        </inputEntry>\n        <inputEntry id="UnaryTests_0yb6s1z">\n          <text>false</text>\n        </inputEntry>\n        <outputEntry id="LiteralExpression_14n15xx">\n          <text>false</text>\n        </outputEntry>\n      </rule>\n    </decisionTable>\n  </decision>\n  <dmndi:DMNDI>\n    <dmndi:DMNDiagram id="DMNDiagram_19nwh5y">\n      <dmndi:DMNShape id="DMNShape_03xv25j" dmnElementRef="decision_0tybghz">\n        <dc:Bounds height="80" width="180" x="150" y="80" />\n      </dmndi:DMNShape>\n    </dmndi:DMNDiagram>\n  </dmndi:DMNDI>\n</definitions>\n',
    }

    create_instance_params = {"input": {"initParametersBytes": json.dumps(param)}}
    url = "http://127.0.0.1:5001/api/v1/namespaces/default/apis/customer2-031b75"

    participant_map = {
        "Participant_1080bkg": {
            "key": "Testmembership-2.org.comMSP::x509::CN=user1,OU=client::CN=ca.testMembership-2.org.com,OU=Fabric,O=testMembership-2.org.com,ST=North Carolina,C=US",
            "fireflyUrl": "http://localhost:5001/api/v1/namespaces/default/apis/customer2-031b75",
        },
        "Participant_0sktaei": {
            "key": "Testmembership-1.org.comMSP::x509::CN=user2,OU=client::CN=ca.testMembership-1.org.com,OU=Fabric,O=testMembership-1.org.com,ST=North Carolina,C=US",
            "fireflyUrl": "http://localhost:5002/api/v1/namespaces/default/apis/customer2-031b75",
        },
        "Participant_1gcdqza": {
            "key": "Testorg-testconsortium.org.comMSP::x509::CN=user3,OU=client::CN=ca.testOrg-testConsortium.org.com,OU=Fabric,O=testOrg-testConsortium.org.com,ST=North Carolina,C=US",
            "fireflyUrl": "http://localhost:5003/api/v1/namespaces/default/apis/customer2-031b75",
        },
    }
    contract_name = "customer2"
    contract_interface_id = "7c366188-80c2-41d0-9dfe-d5634d46f14a"

    if create_listener:
        create_listener_and_subscribe(
            "InstanceCreated",
            contract_name,
            url,
            contract_interface_id,
        )
        create_listener_and_subscribe(
            "Avtivity_continueDone",
            contract_name,
            url,
            contract_interface_id,
        )
    for path in execute_paths:
        single_result = {"path": path, "results": ""}
        res = invoke_task(
            path,
            task.steps,
            url,
            create_instance_params,
            participant_map,
            contract_name,
        )
        single_result["results"] = str(res)
        results.append(single_result)
    return results


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    # Read All Task From All input File, then output it to One File

    match args.command:
        case "help":
            parser.print_help()
        case "run":
            random_mode = ""
            for c in args.m:
                if "a" in c:
                    random_mode += RandomMode.ADD
                elif "r" in c:
                    random_mode += RandomMode.REMOVE
                elif "s" in c:
                    random_mode += RandomMode.SWITCH

            random_num=args.n
            experiment_num=args.N

            append_only_mode = args.e
            if append_only_mode:
                random_mode = ""
                random_num = 0
                experiment_num = 0

            # 标记已完成
            finished_tasks = []
            if os.path.exists(args.output) and not append_only_mode :
                with open(args.output, "r") as f:
                    finished_works = json.load(f)
                    finished_tasks = [task["task_name"] for task in finished_works]

            # 收集所有task
            all_files = (
                [args.input]
                if os.path.isfile(args.input)
                else [args.input + "/" + file for file in os.listdir(args.input)]
            )
            all_content = []
            for file in all_files:
                with open(file, "r") as f:
                    content = json.load(f)
                    for item in content:
                        item["name"] = file + "_" + item["name"]
                    all_content.extend(content)

            all_tasks = [
                step_loader(content)
                for content in all_content
                if content["name"] not in finished_tasks
            ]
            # 执行
            results = []
            with open(args.output + "_output.txt", "a") as f:
                sys.stdout = f  # 将标准输出重定向到文件
                print("output print to file")
                for task in all_tasks:
                    try:
                        res = run_experiment(
                            task=task,
                            random_mode=RandomMode(random_mode),
                            random_num=random_num,
                            experiment_num=experiment_num,
                            create_listener=args.listen,
                        )
                        for r in res:
                            r["index_path"] = r.pop("path")
                            r["path"] = [
                                task.steps[index].element for index in r["index_path"]
                            ]
                    except Exception as e:
                        print(e)
                        continue
                    results.append({"task_name": task.name, "results": res})
                with open(args.output, "r") as f:
                    origin_result = json.load(f)
                with open(args.output, "w") as f:
                    if not append_only_mode:
                        results.extend(origin_result)
                        json.dump(results, f, indent=4)
                    else:
                        # Only append to exists one, never create new task
                        for origin in origin_result:
                            for result in results:
                                if result["task_name"] == origin["task_name"]:
                                    # add all res with different index_path
                                    extra_path = []
                                    for res in result["results"]:
                                        if res["index_path"] not in [
                                            o["index_path"] for o in origin["results"]
                                        ]:
                                            extra_path.append(res)
                                    origin["results"].extend(extra_path)
                        json.dump(origin_result, f, indent=4)
                # 恢复标准输出到控制台
                sys.stdout = sys.__stdout__
                print("这是恢复后，打印到控制台的内容")

        case _:
            default_response()
