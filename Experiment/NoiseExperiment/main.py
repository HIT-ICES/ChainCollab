import itertools
import os
import sys
import json
import argparse
import time
import traceback

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
    parser_run.add_argument(
        "-e", help="append path only mode", action="store_true", default=False
    )
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
    random_method_num=1,  # 一条路径中随机中add swap remove的次数
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
    while len(execute_paths) < experiment_num:
        origin_path = list(range(0, len(task.steps)))
        used_path_remove = list(range(0, len(task.steps)))
        used_path_add = list(itertools.permutations(origin_path, 2))
        used_path_add.extend([(x, len(origin_path)) for x in origin_path])
        used_path_switch = list(itertools.combinations(origin_path, 2))
        random_path = generate_random_path(
            task.invoke_path,
            random_mode,
            random_method_num,
            used_path_add,
            used_path_remove,
            used_path_switch,
        )
        if random_path not in execute_paths:
            execute_paths.append(random_path)
    execute_paths.extend(task.appended_index_paths)
    # execute and output
    results = []

    # copy params here!!!!
    # Param Zone
    ### ----------Param Start----------
    # 1. create instance param：get from frontend
    # 2. contract url in firefly: get from firefly
    # 3. contract interface id: get from firefly

    # param = """{"Participant_1080bkg":{"msp":"Testmembership-2.org.comMSP","attributes":{},"isMulti":false,"multiMaximum":0,"multiMinimum":0,"x509":"eDUwOTo6Q049bWVtYmVyMSxPVT1jbGllbnQ6OkNOPWNhLnRlc3RNZW1iZXJzaGlwLTIub3JnLmNvbSxPVT1GYWJyaWMsTz10ZXN0TWVtYmVyc2hpcC0yLm9yZy5jb20sU1Q9Tm9ydGggQ2Fyb2xpbmEsQz1VUw==@Testmembership-2.org.comMSP"},"Participant_1gcdqza":{"msp":"Testorg-testconsortium.org.comMSP","attributes":{},"isMulti":false,"multiMaximum":0,"multiMinimum":0,"x509":"eDUwOTo6Q049dGVzdE1lbWJlcixPVT1jbGllbnQ6OkNOPWNhLnRlc3RPcmctdGVzdENvbnNvcnRpdW0ub3JnLmNvbSxPVT1GYWJyaWMsTz10ZXN0T3JnLXRlc3RDb25zb3J0aXVtLm9yZy5jb20sU1Q9Tm9ydGggQ2Fyb2xpbmEsQz1VUw==@Testorg-testconsortium.org.comMSP"},"Participant_0sktaei":{"msp":"Testmembership-1.org.comMSP","attributes":{},"isMulti":false,"multiMaximum":0,"multiMinimum":0,"x509":"eDUwOTo6Q049bWVtYmVyMixPVT1jbGllbnQ6OkNOPWNhLnRlc3RNZW1iZXJzaGlwLTEub3JnLmNvbSxPVT1GYWJyaWMsTz10ZXN0TWVtYmVyc2hpcC0xLm9yZy5jb20sU1Q9Tm9ydGggQ2Fyb2xpbmEsQz1VUw==@Testmembership-1.org.comMSP"},"Activity_1yl9tfp_DecisionID":"decision_0tybghz","Activity_1yl9tfp_ParamMapping":{"VIPpoints":"VIPpoints","need_external_provider":"need_external_provider","externalAvailable":"externalAvailable"},"Activity_1yl9tfp_Content":"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<definitions xmlns=\"https://www.omg.org/spec/DMN/20191111/MODEL/\" xmlns:biodi=\"http://bpmn.io/schema/dmn/biodi/2.0\" xmlns:dmndi=\"https://www.omg.org/spec/DMN/20191111/DMNDI/\" xmlns:dc=\"http://www.omg.org/spec/DMN/20180521/DC/\" xmlns:di=\"http://www.omg.org/spec/DMN/20180521/DI/\" id=\"definitions_1olsuce\" name=\"definitions\" namespace=\"http://camunda.org/schema/1.0/dmn\" exporter=\"Camunda Modeler\" exporterVersion=\"5.22.0\">\n  <decision id=\"decision_0tybghz\" name=\"customer1\">\n    <informationRequirement id=\"InformationRequirement_1hoht1b\">\n      <requiredInput href=\"#InputData_1g61x6h\" />\n    </informationRequirement>\n    <informationRequirement id=\"InformationRequirement_0h8ttmr\">\n      <requiredInput href=\"#InputData_04naupt\" />\n    </informationRequirement>\n    <decisionTable id=\"decisionTable_1v3tii8\" hitPolicy=\"FIRST\">\n      <input id=\"input1\" label=\"VIPpoints\" biodi:width=\"192\">\n        <inputExpression id=\"inputExpression1\" typeRef=\"number\">\n          <text>VIPpoints</text>\n        </inputExpression>\n      </input>\n      <input id=\"InputClause_1i7xu16\" label=\"need_external_provider\" biodi:width=\"192\">\n        <inputExpression id=\"LiteralExpression_1hd5g8t\" typeRef=\"boolean\">\n          <text>need_external_provider</text>\n        </inputExpression>\n      </input>\n      <output id=\"output1\" label=\"externalAvailable\" name=\"externalAvailable\" typeRef=\"boolean\" />\n      <rule id=\"DecisionRule_0cs4468\">\n        <inputEntry id=\"UnaryTests_1aut0oo\">\n          <text>&lt;=9999</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0lq0fko\">\n          <text></text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_11etaq9\">\n          <text>false</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_1vbhylp\">\n        <inputEntry id=\"UnaryTests_17t02el\">\n          <text></text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_1ik5kui\">\n          <text>false</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_1amyrv5\">\n          <text>false</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_1l5kdzl\">\n        <inputEntry id=\"UnaryTests_0d8927n\">\n          <text>&gt;=10000</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0bqww61\">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_0z0fcvd\">\n          <text>true</text>\n        </outputEntry>\n      </rule>\n    </decisionTable>\n  </decision>\n  <inputData id=\"InputData_1g61x6h\" name=\"VIPpoints\" />\n  <inputData id=\"InputData_04naupt\" name=\"need_external_provider\" />\n  <dmndi:DMNDI>\n    <dmndi:DMNDiagram id=\"DMNDiagram_1flr508\">\n      <dmndi:DMNShape id=\"DMNShape_0fg1a7g\" dmnElementRef=\"decision_0tybghz\">\n        <dc:Bounds height=\"80\" width=\"180\" x=\"460\" y=\"70\" />\n      </dmndi:DMNShape>\n      <dmndi:DMNShape id=\"DMNShape_0g5yhqk\" dmnElementRef=\"InputData_1g61x6h\">\n        <dc:Bounds height=\"45\" width=\"125\" x=\"258\" y=\"238\" />\n      </dmndi:DMNShape>\n      <dmndi:DMNShape id=\"DMNShape_1inp6do\" dmnElementRef=\"InputData_04naupt\">\n        <dc:Bounds height=\"45\" width=\"125\" x=\"678\" y=\"258\" />\n      </dmndi:DMNShape>\n      <dmndi:DMNEdge id=\"DMNEdge_06eiibn\" dmnElementRef=\"InformationRequirement_1hoht1b\">\n        <di:waypoint x=\"321\" y=\"238\" />\n        <di:waypoint x=\"520\" y=\"170\" />\n        <di:waypoint x=\"520\" y=\"150\" />\n      </dmndi:DMNEdge>\n      <dmndi:DMNEdge id=\"DMNEdge_1qs00fv\" dmnElementRef=\"InformationRequirement_0h8ttmr\">\n        <di:waypoint x=\"741\" y=\"258\" />\n        <di:waypoint x=\"580\" y=\"170\" />\n        <di:waypoint x=\"580\" y=\"150\" />\n      </dmndi:DMNEdge>\n    </dmndi:DMNDiagram>\n  </dmndi:DMNDI>\n</definitions>\n","Activity_0ibsbry_DecisionID":"decision_0tybghz","Activity_0ibsbry_ParamMapping":{"invoiceType":"invoiceType","invoice":"invoice","invoiceTypeAvailable":"invoiceAvailable"},"Activity_0ibsbry_Content":"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<definitions xmlns=\"https://www.omg.org/spec/DMN/20191111/MODEL/\" xmlns:biodi=\"http://bpmn.io/schema/dmn/biodi/2.0\" xmlns:dmndi=\"https://www.omg.org/spec/DMN/20191111/DMNDI/\" xmlns:dc=\"http://www.omg.org/spec/DMN/20180521/DC/\" id=\"definitions_1olsuce\" name=\"definitions\" namespace=\"http://camunda.org/schema/1.0/dmn\" exporter=\"Camunda Modeler\" exporterVersion=\"5.22.0\">\n  <decision id=\"decision_0tybghz\" name=\"customer2\">\n    <decisionTable id=\"decisionTable_1v3tii8\" hitPolicy=\"FIRST\">\n      <input id=\"input1\" label=\"invoiceType\" biodi:width=\"192\">\n        <inputExpression id=\"inputExpression1\" typeRef=\"string\">\n          <text>invoiceType</text>\n        </inputExpression>\n      </input>\n      <input id=\"InputClause_02k362l\" label=\"invoice\">\n        <inputExpression id=\"LiteralExpression_1uexm9z\" typeRef=\"boolean\">\n          <text>invoice</text>\n        </inputExpression>\n      </input>\n      <output id=\"output1\" label=\"invoiceTypeAvailable\" name=\"invoiceTypeAvailable\" typeRef=\"boolean\" biodi:width=\"192\" />\n      <rule id=\"DecisionRule_1oyddrr\">\n        <inputEntry id=\"UnaryTests_1wvkvfa\">\n          <text>\"HIT\"</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0xgibym\">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_1esf1bm\">\n          <text>true</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_0f5g2m7\">\n        <inputEntry id=\"UnaryTests_069nkt8\">\n          <text>\"HITwh\"</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0m8uhu2\">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_0cm8blh\">\n          <text>true</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_0bo63a3\">\n        <inputEntry id=\"UnaryTests_1dkdmmv\">\n          <text></text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_086c8ll\">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_0rhhni5\">\n          <text>false</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_1wdnie7\">\n        <inputEntry id=\"UnaryTests_0t432ic\">\n          <text></text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0yb6s1z\">\n          <text>false</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_14n15xx\">\n          <text>false</text>\n        </outputEntry>\n      </rule>\n    </decisionTable>\n  </decision>\n  <dmndi:DMNDI>\n    <dmndi:DMNDiagram id=\"DMNDiagram_19nwh5y\">\n      <dmndi:DMNShape id=\"DMNShape_03xv25j\" dmnElementRef=\"decision_0tybghz\">\n        <dc:Bounds height=\"80\" width=\"180\" x=\"150\" y=\"80\" />\n      </dmndi:DMNShape>\n    </dmndi:DMNDiagram>\n  </dmndi:DMNDI>\n</definitions>\n"}"""
    param={
  "Participant_09cjol2": {
    "msp": "Mem3.org.comMSP",
    "attributes": {},
    "isMulti": False,
    "multiMaximum": 0,
    "multiMinimum": 0,
    "x509": "eDUwOTo6Q049VXNlcjMsT1U9Y2xpZW50OjpDTj1jYS5tZW0zLm9yZy5jb20sT1U9RmFicmljLE89bWVtMy5vcmcuY29tLFNUPU5vcnRoIENhcm9saW5hLEM9VVM=@Mem3.org.comMSP"
  },
  "Participant_0w6qkdf": {
    "msp": "Organization-consortium.org.comMSP",
    "attributes": {},
    "isMulti": False,
    "multiMaximum": 0,
    "multiMinimum": 0,
    "x509": "eDUwOTo6Q049VXNlcjEsT1U9Y2xpZW50OjpDTj1jYS5Pcmdhbml6YXRpb24tQ29uc29ydGl1bS5vcmcuY29tLE9VPUZhYnJpYyxPPU9yZ2FuaXphdGlvbi1Db25zb3J0aXVtLm9yZy5jb20sU1Q9Tm9ydGggQ2Fyb2xpbmEsQz1VUw==@Organization-consortium.org.comMSP"
  },
  "Participant_19mgbdn": {
    "msp": "Mem2.org.comMSP",
    "attributes": {},
    "isMulti": False,
    "multiMaximum": 0,
    "multiMinimum": 0,
    "x509": "eDUwOTo6Q049VXNlcjIsT1U9Y2xpZW50OjpDTj1jYS5tZW0yLm9yZy5jb20sT1U9RmFicmljLE89bWVtMi5vcmcuY29tLFNUPU5vcnRoIENhcm9saW5hLEM9VVM=@Mem2.org.comMSP"
  },
  "Participant_0sa2v7d": {
    "msp": "Mem3.org.comMSP",
    "attributes": {},
    "isMulti": False,
    "multiMaximum": 0,
    "multiMinimum": 0,
    "x509": "eDUwOTo6Q049VXNlcjMsT1U9Y2xpZW50OjpDTj1jYS5tZW0zLm9yZy5jb20sT1U9RmFicmljLE89bWVtMy5vcmcuY29tLFNUPU5vcnRoIENhcm9saW5hLEM9VVM=@Mem3.org.comMSP"
  },
  "Participant_19j1e3o": {
    "msp": "Mem3.org.comMSP",
    "attributes": {},
    "isMulti": False,
    "multiMaximum": 0,
    "multiMinimum": 0,
    "x509": "eDUwOTo6Q049VXNlcjMsT1U9Y2xpZW50OjpDTj1jYS5tZW0zLm9yZy5jb20sT1U9RmFicmljLE89bWVtMy5vcmcuY29tLFNUPU5vcnRoIENhcm9saW5hLEM9VVM=@Mem3.org.comMSP"
  },
  "Activity_0rm8bkp_DecisionID": "Decision_0zwjfyy",
  "Activity_0rm8bkp_ParamMapping": {
    "numberOfUnits": "numberOfUnits",
    "urgent": "urgent",
    "supplierReputation": "supplierReputation",
    "finalPriority": "finalPriority"
  },
  "Activity_0rm8bkp_Content": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<definitions xmlns=\"https://www.omg.org/spec/DMN/20191111/MODEL/\" xmlns:dmndi=\"https://www.omg.org/spec/DMN/20191111/DMNDI/\" xmlns:dc=\"http://www.omg.org/spec/DMN/20180521/DC/\" xmlns:di=\"http://www.omg.org/spec/DMN/20180521/DI/\" id=\"definitions_1olsuce\" name=\"definitions\" namespace=\"http://camunda.org/schema/1.0/dmn\" exporter=\"dmn-js (https://demo.bpmn.io/dmn)\" exporterVersion=\"16.4.0\">\n  <decision id=\"decision_0tybghz\" name=\"Initial Priority Decision\">\n    <informationRequirement id=\"InformationRequirement_1yax2nr\">\n      <requiredInput href=\"#InputData_0x10kua\" />\n    </informationRequirement>\n    <informationRequirement id=\"InformationRequirement_0968tcf\">\n      <requiredInput href=\"#InputData_19y9i1v\" />\n    </informationRequirement>\n    <decisionTable id=\"decisionTable_1v3tii8\">\n      <input id=\"input1\" label=\"numberOfUnits\">\n        <inputExpression id=\"inputExpression1\" typeRef=\"number\">\n          <text>numberOfUnits</text>\n        </inputExpression>\n      </input>\n      <input id=\"InputClause_0pvns0w\" label=\"urgent\">\n        <inputExpression id=\"LiteralExpression_08nncbj\" typeRef=\"boolean\">\n          <text>urgent</text>\n        </inputExpression>\n      </input>\n      <output id=\"output1\" label=\"initialPriority\" name=\"initialPriority\" typeRef=\"string\" />\n      <rule id=\"DecisionRule_0u3ic44\">\n        <inputEntry id=\"UnaryTests_0ju5tlr\">\n          <text>&lt;100</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_05vb8be\">\n          <text></text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_17p1hon\">\n          <text>\"Low\"</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_0nwm2gu\">\n        <inputEntry id=\"UnaryTests_01oe1uf\">\n          <text>[100..500)</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0gr116d\">\n          <text>False</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_07fd2cz\">\n          <text>\"Medium\"</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_0uz5tzx\">\n        <inputEntry id=\"UnaryTests_0se9tkd\">\n          <text>[100..500)</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0hmxfz8\">\n          <text>true</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_0p3cwai\">\n          <text>\"High\"</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_09xhvy9\">\n        <inputEntry id=\"UnaryTests_1oq4wlh\">\n          <text>&gt;=500</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0ujggp2\">\n          <text></text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_10me9jn\">\n          <text>\"High\"</text>\n        </outputEntry>\n      </rule>\n    </decisionTable>\n  </decision>\n  <inputData id=\"InputData_0x10kua\" name=\"numberOfUnits\" />\n  <inputData id=\"InputData_19y9i1v\" name=\"urgent\" />\n  <decision id=\"Decision_0zwjfyy\" name=\"Final Priority Adjustment Decision\">\n    <informationRequirement id=\"InformationRequirement_0hefcti\">\n      <requiredDecision href=\"#decision_0tybghz\" />\n    </informationRequirement>\n    <informationRequirement id=\"InformationRequirement_1o26uw3\">\n      <requiredInput href=\"#InputData_01mbjhm\" />\n    </informationRequirement>\n    <decisionTable id=\"DecisionTable_1c43yo6\">\n      <input id=\"InputClause_14snh1s\" label=\"initialPriority\">\n        <inputExpression id=\"LiteralExpression_0zgz0u7\" typeRef=\"string\">\n          <text>initialPriority</text>\n        </inputExpression>\n      </input>\n      <input id=\"InputClause_0r7er56\" label=\"supplierReputation\">\n        <inputExpression id=\"LiteralExpression_14je7bl\" typeRef=\"number\">\n          <text>supplierReputation</text>\n        </inputExpression>\n      </input>\n      <output id=\"OutputClause_0ugy0r3\" label=\"finalPriority\" name=\"finalPriority\" typeRef=\"string\" />\n      <rule id=\"DecisionRule_1ji9p5q\">\n        <inputEntry id=\"UnaryTests_0gywq2x\">\n          <text>\"Low\"</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_1ly0kl0\">\n          <text>&lt;3</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_17ybt1a\">\n          <text>\"VeryLow\"</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_0een4yz\">\n        <inputEntry id=\"UnaryTests_1jnrzhz\">\n          <text>\"Low\"</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_1cp09o7\">\n          <text>&gt;=3</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_0g6h3ee\">\n          <text>\"Low\"</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_11u4ema\">\n        <inputEntry id=\"UnaryTests_0dgckdn\">\n          <text>\"Medium\"</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_06ekcvf\">\n          <text>&lt;3</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_0jpckpc\">\n          <text>\"Low\"</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_0qtj8y9\">\n        <inputEntry id=\"UnaryTests_0pzq72r\">\n          <text>\"Medium\"</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_1xk645h\">\n          <text>&gt;=3</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_039dz01\">\n          <text>\"Medium\"</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_0atuqz7\">\n        <inputEntry id=\"UnaryTests_0v84h5u\">\n          <text>\"High\"</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_07e4eq2\">\n          <text>&lt;3</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_1qg56xq\">\n          <text>\"Medium\"</text>\n        </outputEntry>\n      </rule>\n      <rule id=\"DecisionRule_1df3y7p\">\n        <inputEntry id=\"UnaryTests_0rpua0h\">\n          <text>\"High\"</text>\n        </inputEntry>\n        <inputEntry id=\"UnaryTests_0b3aoo8\">\n          <text>&gt;=3</text>\n        </inputEntry>\n        <outputEntry id=\"LiteralExpression_1y9o94k\">\n          <text>\"High\"</text>\n        </outputEntry>\n      </rule>\n    </decisionTable>\n  </decision>\n  <inputData id=\"InputData_01mbjhm\" name=\"supplierReputation\" />\n  <dmndi:DMNDI>\n    <dmndi:DMNDiagram id=\"DMNDiagram_14swko0\">\n      <dmndi:DMNShape id=\"DMNShape_1ujfuig\" dmnElementRef=\"decision_0tybghz\">\n        <dc:Bounds height=\"80\" width=\"180\" x=\"150\" y=\"150\" />\n      </dmndi:DMNShape>\n      <dmndi:DMNShape id=\"DMNShape_0ih0fma\" dmnElementRef=\"InputData_0x10kua\">\n        <dc:Bounds height=\"45\" width=\"125\" x=\"17\" y=\"307\" />\n      </dmndi:DMNShape>\n      <dmndi:DMNEdge id=\"DMNEdge_1ki7x9b\" dmnElementRef=\"InformationRequirement_1yax2nr\">\n        <di:waypoint x=\"80\" y=\"307\" />\n        <di:waypoint x=\"210\" y=\"250\" />\n        <di:waypoint x=\"210\" y=\"230\" />\n      </dmndi:DMNEdge>\n      <dmndi:DMNShape id=\"DMNShape_1hcq2mc\" dmnElementRef=\"InputData_19y9i1v\">\n        <dc:Bounds height=\"45\" width=\"125\" x=\"257\" y=\"307\" />\n      </dmndi:DMNShape>\n      <dmndi:DMNEdge id=\"DMNEdge_1o1ier2\" dmnElementRef=\"InformationRequirement_0968tcf\">\n        <di:waypoint x=\"320\" y=\"307\" />\n        <di:waypoint x=\"270\" y=\"250\" />\n        <di:waypoint x=\"270\" y=\"230\" />\n      </dmndi:DMNEdge>\n      <dmndi:DMNShape id=\"DMNShape_0zormdd\" dmnElementRef=\"Decision_0zwjfyy\">\n        <dc:Bounds height=\"80\" width=\"180\" x=\"280\" y=\"-20\" />\n      </dmndi:DMNShape>\n      <dmndi:DMNEdge id=\"DMNEdge_0k1jr3i\" dmnElementRef=\"InformationRequirement_0hefcti\">\n        <di:waypoint x=\"240\" y=\"150\" />\n        <di:waypoint x=\"340\" y=\"80\" />\n        <di:waypoint x=\"340\" y=\"60\" />\n      </dmndi:DMNEdge>\n      <dmndi:DMNShape id=\"DMNShape_1txv6gd\" dmnElementRef=\"InputData_01mbjhm\">\n        <dc:Bounds height=\"45\" width=\"125\" x=\"417\" y=\"167\" />\n      </dmndi:DMNShape>\n      <dmndi:DMNEdge id=\"DMNEdge_1geh2p0\" dmnElementRef=\"InformationRequirement_1o26uw3\">\n        <di:waypoint x=\"480\" y=\"167\" />\n        <di:waypoint x=\"400\" y=\"80\" />\n        <di:waypoint x=\"400\" y=\"60\" />\n      </dmndi:DMNEdge>\n    </dmndi:DMNDiagram>\n  </dmndi:DMNDI>\n</definitions>\n"
}
    url="http://127.0.0.1:5001/api/v1/namespaces/default/apis/paperNew-dd704b"
    contract_name="paperNew"
    

    create_instance_params = {"input": {"initParametersBytes": json.dumps(param)}}
    contract_interface_id = "477bc530-3828-4d3b-89c6-adc1bdfad210"

    participant_map = {
        "Participant_19mgbdn": {
            "key": "Mem2.org.comMSP::x509::CN=User2,OU=client::CN=ca.mem2.org.com,OU=Fabric,O=mem2.org.com,ST=North Carolina,C=US",
            "fireflyUrl": "http://localhost:5001/api/v1/namespaces/default/apis/paperNew-dd704b",
        },
        "Participant_0w6qkdf": {
            "key": "Organization-consortium.org.comMSP::x509::CN=User1,OU=client::CN=ca.Organization-Consortium.org.com,OU=Fabric,O=Organization-Consortium.org.com,ST=North Carolina,C=US",
            "fireflyUrl": "http://localhost:5003/api/v1/namespaces/default/apis/paperNew-dd704b",
        },
        "Participant_09cjol2": {
            "key": "Mem3.org.comMSP::x509::CN=User3,OU=client::CN=ca.mem3.org.com,OU=Fabric,O=mem3.org.com,ST=North Carolina,C=US",
            "fireflyUrl": "http://localhost:5002/api/v1/namespaces/default/apis/paperNew-dd704b",
        },
        "Participant_0sa2v7d": {
            "key": "Mem3.org.comMSP::x509::CN=User3,OU=client::CN=ca.mem3.org.com,OU=Fabric,O=mem3.org.com,ST=North Carolina,C=US",
            "fireflyUrl": "http://localhost:5002/api/v1/namespaces/default/apis/paperNew-dd704b",
        },
        "Participant_19j1e3o": {
            "key": "Mem3.org.comMSP::x509::CN=User3,OU=client::CN=ca.mem3.org.com,OU=Fabric,O=mem3.org.com,ST=North Carolina,C=US",
            "fireflyUrl": "http://localhost:5002/api/v1/namespaces/default/apis/paperNew-dd704b",
        }
    }

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

            append_only_mode = args.e
            if append_only_mode:
                random_mode = ""
                random_num = 0

            # 标记已完成
            finished_tasks = []
            if os.path.exists(args.output) and not append_only_mode:
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

            random_num = args.n
            rate = args.N * 0.01
            experiment_num = [
                int(
                    (
                        len(task.steps) * (len(task.steps))
                        + len(task.steps)
                        + 0.5 * len(task.steps) * (len(task.steps) - 1)
                    )
                    * rate
                )
                for task in all_tasks
            ]
            print(experiment_num)

            # 执行
            results = []
            passNum = 0
            errorNum = 0
            failNum = 0

            with open(args.output + "_output.txt", "a") as f:
                sys.stdout = f  # 将标准输出重定向到文件
                print("output print to file")
                for idx, task in enumerate(all_tasks):
                    try:
                        res = run_experiment(
                            task=task,
                            random_mode=RandomMode(random_mode),
                            random_method_num=random_num,
                            experiment_num=experiment_num[
                                idx
                            ],  # Use the calculated value
                            create_listener=args.listen,
                        )
                        for r in res:
                            r["index_path"] = r.pop("path")
                            r["path"] = [
                                task.steps[index].element for index in r["index_path"]
                            ]
                            if r["results"] == "All steps passed":
                                r["tag"] = 0
                                passNum = passNum + 1
                            elif r["index_path"][0] == 0 and r["results"].startswith(
                                "Step 0"
                            ):
                                r["tag"] = 1
                                errorNum = errorNum + 1
                            else:
                                r["tag"] = 2
                                failNum = failNum + 1
                    except Exception as e:
                        traceback.print_exc()
                        print(e)
                        continue
                    count = (
                        "succeed:"
                        + str(passNum)
                        + ",error:"
                        + str(errorNum)
                        + ",fail:"
                        + str(failNum)
                    )
                    results.append(
                        {"task_name": task.name, "results": res, "count": count}
                    )
                if os.path.exists(args.output):
                    with open(args.output, "r") as f:
                        origin_result = json.load(f)
                else:
                    origin_result = []
                with open(args.output, "w") as f:
                    if not append_only_mode:
                        results.extend(origin_result)
                        json.dump(results, f, indent=4)
                    else:
                        # Only append to existing one, never create a new task
                        for origin in origin_result:
                            for result in results:
                                if result["task_name"] == origin["task_name"]:
                                    # Add all res with different index_path
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
                print(len(res))
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())))

        case _:
            default_response()
