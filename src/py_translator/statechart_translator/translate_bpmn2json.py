'''
1.提取所有元素的重要信息,并使用写好的Parallel算法处理成层次结构
dataMap={
    "element_id":{
        "name":None,
        "targetName":None,
        "type":None,
        "params":{
            "type":{
                "is_mutiparticipant":False,
                "is_mutitask_loop":False,
                "is_mutitask_loop_condition":False,
                "is_mutitask_parallel":False
            },
            "mutiParticipant":{
                "max":3,
                "mutiparticipantName":"aaa",
            },
            "mutiTask":{
                "loopMax":3,
                "LoopConditionExpression":"aaa",
                "ParallelNum":3
            },
            "DMN":{
                "DMNOutputNameList":[]
            },
            "ExclusiveGateway":{
                "targetList":[
                    {
                        "targetName":"aaa",
                        "condition":"aaa"
                    }
                ]
            },
            "EventGateway":{
                "targetList":[
                    {
                        "targetName":"aaa",
                        "event":"aaa"
                    }
                ]
            }
        }
    }
    "parallelGateway_next":{
            "parallGatewat_end_id":"target_id"
        }
    "start_event":{
        "element_id":"target_id"
    }
    "end_event":[
        "element_id1",
        "element_id2"
    ]
}
   
2.根据 
     1.层次结构
     2.每个元素的类型 
  来递归添加状态机json




  exlusiveGateway      的   condition
  mutiTask_顺序多实例   的   loop_max 
  mutiTask_带跳出循环   的   loop_condition
  mutiTask_并行多实例   的   parallel_num
  
  eventGateway的event怎么表示? 后续给状态机发送一条边的id?

'''


# 存在的问题： 1.不支持的属性目前写死为字符串
#             2.ExclusiveGateway没有condition的情况(收束)待完善
#             3.ParallelGateway后面紧跟着嵌套ParallelGateway的情况无法处理
#             4.不支持双muti
#             5.condition未写FEEL表达式支持
              


from enum import Enum
import json
from statechart_translator.snippet import XstateJSONElement

from statechart_translator.parser import Choreography
from pprint import pprint
from copy import deepcopy
from statechart_translator.elements import (
    Element,
    StartEvent,
    ParallelGateway,
    ExclusiveGateway,
    EventBasedGateway,
    NodeType,
    EdgeType,
    EndEvent,
    TaskLoopType
)
from statechart_translator.ParallelGateway import method_to_extract_parallel_gateway


def handle_targetName(flowElement,pairs):
    # 处理后接choreographyTask
    if flowElement.target.type==NodeType.CHOREOGRAPHY_TASK:
        if flowElement.target.init_participant.id == flowElement.target.message_flows[0].source.id:
            return flowElement.target.message_flows[0].message.id
        else:
            return flowElement.target.message_flows[1].message.id
    #处理后接gatewayMachine
    if flowElement.target.type==NodeType.PARALLEL_GATEWAY:
        for pair in pairs:
            if pair.find(flowElement.target.id) != -1:
                return pair
    
               
    return flowElement.target.id


def extract_element_info(element: Element,pairs,globalVariable=None):
    metaData = {
        "type": element.type,
        "name": element.id,
        "targetName": None,
        "params": {
            "type":{
                "is_mutiparticipant":False,
                "is_mutitask_loop":False,
                "is_mutitask_loop_condition":False,
                "is_mutitask_parallel":False
            },
            "mutiParticipant":{
                "max":None,
                "mutiparticipantName":None,
            },
            "mutiTask":{
                "loopMax":None,
                "LoopConditionExpression":None,
                "ParallelNum":None
            },
            "DMN":{
                "DMNOutputNameList":[]
            },
            "ExclusiveGateway":{
                "targetList":[]
            },
            "EventGateway":{
                "targetList":[]
            },
            "ChoreographyTaskName":None,
            "MessageGlobalVariable":[]
        }
    }
    if element.type==NodeType.END_EVENT or element.type==NodeType.PARALLEL_GATEWAY or element.type==NodeType.EXCLUSIVE_GATEWAY or element.type==NodeType.EVENT_BASED_GATEWAY:
        metaData["targetName"] =None
    #处理支线结束节点
    elif element.outgoing.target.type==NodeType.PARALLEL_GATEWAY and len(element.outgoing.target.outgoings)==1:
        metaData["targetName"] = "done"
    else:
        metaData["targetName"] = handle_targetName(element.outgoing,pairs)
    

    if element.type==NodeType.END_EVENT:
        return element.id
    
    if element.type==NodeType.START_EVENT:
        return [element.id,handle_targetName(element.outgoing,pairs)]

    #处理排他网关
    if element.type==NodeType.EXCLUSIVE_GATEWAY:
        metaData["params"]["ExclusiveGateway"]["targetList"] = [{"targetName":handle_targetName(edge,pairs),"condition":edge.name if edge.name != "" else None} for edge in element.outgoings]

        set1 = set()
        for outgoing in element.outgoings:
            variables = extract_variable_names(outgoing.name)
            set1.update(variables)

        return metaData
    

    #处理事件网关
    if element.type==NodeType.EVENT_BASED_GATEWAY:
        metaData["params"]["EventGateway"]["targetList"] = [{"targetName":handle_targetName(edge,pairs),"event":edge.id} for edge in element.outgoings]
        return metaData
    #处理DMN
    if element.type==NodeType.BUSINESS_RULE_TASK:
        parsed_data = json.loads(element.documentation)
        output_names = [output['name'] for output in parsed_data['outputs']]
        metaData["params"]["DMN"]["DMNOutputNameList"] = output_names
        return metaData
    
    if element.type==NodeType.PARALLEL_GATEWAY:
        return [handle_targetName(edge,pairs) for edge in element.outgoings]

    #处理task
    if element.type==NodeType.CHOREOGRAPHY_TASK:
        metaData["params"]["ChoreographyTaskName"] = element.id


        if hasattr(element,"loop_type"):
            match element.loop_type:
                case TaskLoopType.STANDARD:
                    metaData["params"]["mutiTask"]["loopMax"] = element.loop_cardinality
                    metaData["params"]["type"]["is_mutitask_loop"] = True
                    metaData["params"]["mutiTask"]["LoopConditionExpression"] = element.completion_condition
                    metaData["params"]["type"]["is_mutitask_loop_condition"] = True
                case TaskLoopType.MULTI_INSTANCE_PARALLEL:
                    metaData["params"]["mutiTask"]["ParallelNum"] = element.loop_cardinality
                    metaData["params"]["type"]["is_mutitask_parallel"] = True   
                case TaskLoopType.MULTI_INSTANCE_SEQUENTIAL:
                    metaData["params"]["mutiTask"]["loopMax"] = element.loop_cardinality
                    metaData["params"]["type"]["is_mutitask_loop"] = True
                case "None":
                    pass
        
        metaData1 = deepcopy(metaData)
        metaData2 = deepcopy(metaData)


        def extract_global_variable(document,metaData):
            parsed_data = json.loads(document)
            if parsed_data["properties"] != "":
                for key in parsed_data["properties"].keys():
                    if key in globalVariable:
                        metaData["params"]["MessageGlobalVariable"].append(key)
            return metaData


        if len(element.message_flows)==2:
            if element.init_participant.id == element.message_flows[0].source.id:
                metaData1 = extract_global_variable(element.message_flows[0].message.documentation,metaData1)
                metaData1["name"] = element.message_flows[0].message.id
                metaData2 = extract_global_variable(element.message_flows[1].message.documentation,metaData2)
                metaData2["name"] = element.message_flows[1].message.id
            else:
                metaData1 = extract_global_variable(element.message_flows[1].message.documentation,metaData1)
                metaData1["name"] = element.message_flows[1].message.id
                metaData2 = extract_global_variable(element.message_flows[0].message.documentation,metaData2)
                metaData2["name"] = element.message_flows[0].message.id

            if hasattr(element,"participants"):
                #未考虑双muti
                if element.participants[0].is_multi:
                    metaData1["params"]["mutiParticipant"]["max"] = element.participants[0].multi_maximum
                    metaData1["params"]["mutiParticipant"]["mutiparticipantName"] = element.participants[0].id
                    metaData1["params"]["type"]["is_mutiparticipant"] = True
                    metaData2["params"]["mutiParticipant"]["max"] = element.participants[0].multi_maximum
                    metaData2["params"]["mutiParticipant"]["mutiparticipantName"] = element.participants[0].id
                    metaData2["params"]["type"]["is_mutiparticipant"] = True
                if element.participants[1].is_multi:
                    metaData1["params"]["mutiParticipant"]["max"] = element.participants[1].multi_maximum
                    metaData1["params"]["mutiParticipant"]["mutiparticipantName"] = element.participants[1].id
                    metaData1["params"]["type"]["is_mutiparticipant"] = True
                    metaData2["params"]["mutiParticipant"]["max"] = element.participants[1].multi_maximum
                    metaData2["params"]["mutiParticipant"]["mutiparticipantName"] = element.participants[1].id
                    metaData2["params"]["type"]["is_mutiparticipant"] = True

            return [metaData1,metaData2]
        elif len(element.message_flows)==1:
            metaData1["name"] = element.message_flows[0].message.id
            metaData1 = extract_global_variable(element.message_flows[0].message.documentation,metaData1)
            if hasattr(element,"participants"):
                #未考虑双muti
                if element.participants[0].is_multi:
                    metaData1["params"]["mutiParticipant"]["max"] = element.participants[0].multi_maximum
                    metaData1["params"]["mutiParticipant"]["mutiparticipantName"] = element.participants[0].id
                    metaData1["params"]["type"]["is_mutiparticipant"] = True
                if element.participants[1].is_multi:
                    metaData1["params"]["mutiParticipant"]["max"] = element.participants[1].multi_maximum
                    metaData1["params"]["mutiParticipant"]["mutiparticipantName"] = element.participants[1].id
                    metaData1["params"]["type"]["is_mutiparticipant"] = True
            return [metaData1]

    return metaData


import re
def extract_variable_names(expression):
    # 匹配变量名（字母、数字和下划线组成，不能以数字开头）
    variable_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'

    # 匹配字符串常量
    string_pattern = r'"([^"]*)"'
    
    # 找到所有的字符串常量
    strings = re.findall(string_pattern, expression)
    
    # 找到所有匹配的变量名
    variable_names = re.findall(variable_pattern, expression)
    
    # 创建一个集合来去重，并排除字符串常量
    unique_variable_names = {var for var in variable_names if var not in strings}
    
    return unique_variable_names

def get_element_machineInfo(choreography:Choreography,pairs):
    
    dataMap = {
        "parallelGateway_next":{},
        "start_event":[],
        "end_event":[],
        "globalVariable":set()
    }

    ExclusiveGateways = choreography.query_element_with_type(NodeType.EXCLUSIVE_GATEWAY)
    EventBasedGateways = choreography.query_element_with_type(NodeType.EVENT_BASED_GATEWAY)
    for element in ExclusiveGateways:
        dataMap[element.id] = extract_element_info(element,pairs)
        set1 = set()
        for outgoing in element.outgoings:
            variables = extract_variable_names(outgoing.name)
            set1.update(variables)
        dataMap["globalVariable"].update(set1)

    for element in EventBasedGateways:
        dataMap[element.id] = extract_element_info(element,pairs)


    choreographyTasks = choreography.query_element_with_type(NodeType.CHOREOGRAPHY_TASK)
    for element in choreographyTasks:
        dataMap[element.id]=[]
        ordered_messages = extract_element_info(element,pairs,dataMap["globalVariable"])
        for message in ordered_messages:
            dataMap[element.id].append(message)

        for message in ordered_messages:
            json.loads(element.message_flows[0].message.documentation)
    
    

    businessRules = choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK)
    for element in businessRules:
        dataMap[element.id] = extract_element_info(element,pairs)

    ParallelGateways = choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY)
    for element in ParallelGateways:
        dataMap["parallelGateway_next"][element.id] = extract_element_info(element,pairs)

    

    endEvents = choreography.query_element_with_type(NodeType.END_EVENT)
    for element in endEvents:
        dataMap["end_event"].append(extract_element_info(element,pairs))

    startEvent = choreography.query_element_with_type(NodeType.START_EVENT)[0]
    dataMap["start_event"].extend(extract_element_info(startEvent,pairs))

    



    # for key, data in dataMap.items():
    #     print({key: data})
    
    return dataMap


def DFS_translate(tree, currentMachine,dataMap,xstateJSONElement):
 
    for node in tree["direct_elements"]:
        if node in list(dataMap.keys()):
            if isinstance(dataMap[node],list):
                for message in dataMap[node]:
                    addMachine(currentMachine, message,xstateJSONElement)
            else:
                addMachine(currentMachine, dataMap[node],xstateJSONElement)

    for branch in tree["nested_machines"]:
        childrenName = branch["start_element"]+"_TO_"+ branch["end_element"]
        
        currentMachine["states"][childrenName] = {
            "initial": "",
            "states": {},
            "onDone": [],
            "type": "parallel",
        }
        xstateJSONElement.SetOndone(currentMachine["states"][childrenName],dataMap["parallelGateway_next"][branch["end_element"]][0])

    for branch in tree["nested_machines"]:
        childrenName = branch["start_element"]+"_TO_"+ branch["end_element"]
        initElement = ""
        for Element in branch["direct_elements"]:
            for nextElement in dataMap["parallelGateway_next"][branch["start_element"]]:
                #如果initElement是message
                if isinstance(dataMap[Element],list):
                    for messageElement in dataMap[Element]:
                        if nextElement==messageElement["name"]:
                            initElement = nextElement
                else: 
                    if nextElement==dataMap[Element]["name"]:
                        #如果initElement是并行网关状态机 TODO
                        if dataMap[Element]["type"] == NodeType.PARALLEL_GATEWAY:
                            initElement = "f(pair)"
                        initElement = nextElement
        currentMachine["states"][childrenName]["states"][branch["machine_name"]]={
            "initial": initElement,
            "states": {
                "done":{
                    "type":"final"
                }
            },
            "onDone": []
        }

    for branch in tree["nested_machines"]:
        childrenName = branch["start_element"]+"_TO_"+ branch["end_element"]
        # xstateJSONElement.SetOndone(currentMachine["states"][childrenName],dataMap["parallelGateway_next"][branch["end_element"]])       
        DFS_translate(branch, currentMachine["states"][childrenName]["states"][branch["machine_name"]], dataMap,xstateJSONElement)
   
        
def addMachine(currentMachine, data,xstateJSONElement):
    match data["type"]:
        case NodeType.EXCLUSIVE_GATEWAY:
            xstateJSONElement.ExclusiveGatewayMachine(currentMachine,data["params"]["ExclusiveGateway"]["targetList"],data["name"])
        case NodeType.EVENT_BASED_GATEWAY:
            xstateJSONElement.EventGatewayMachine(currentMachine,data["params"]["EventGateway"]["targetList"],data["name"])
        case NodeType.BUSINESS_RULE_TASK:
            xstateJSONElement.DMNMachine(currentMachine,data["name"],data["params"]["DMN"]["DMNOutputNameList"],data["targetName"])
        case NodeType.CHOREOGRAPHY_TASK:
            if data["params"]["type"]["is_mutiparticipant"]:
                if data["params"]["type"]["is_mutitask_loop_condition"]:
                    xstateJSONElement.MutiTaskLoopMachine(currentMachine, data["name"], data["params"]["mutiTask"]["loopMax"], data["params"]["mutiTask"]["LoopConditionExpression"], True, data["targetName"],{"max":data["params"]["mutiParticipant"]["max"],"participantName":data["params"]["mutiParticipant"]["mutiparticipantName"]})
                elif data["params"]["type"]["is_mutitask_loop"]:
                    xstateJSONElement.MutiTaskLoopMachine(currentMachine, data["name"], data["params"]["mutiTask"]["loopMax"], None, True, data["targetName"],{"max":data["params"]["mutiParticipant"]["max"],"participantName":data["params"]["mutiParticipant"]["mutiparticipantName"]})
                elif data["params"]["type"]["is_mutitask_parallel"]:
                    xstateJSONElement.MutiTaskPallelMachine(currentMachine,data["name"], data["params"]["mutiParticipant"]["max"], True, data["targetName"],{"max":data["params"]["mutiParticipant"]["max"],"participantName":data["params"]["mutiParticipant"]["mutiparticipantName"]})
                else:
                    xstateJSONElement.ChooseMutiParticipantMachine(currentMachine, data["name"], data["params"]["mutiParticipant"]["max"], data["params"]["mutiParticipant"]["mutiparticipantName"], data["targetName"])
            else:
                if data["params"]["type"]["is_mutitask_loop_condition"]:
                    xstateJSONElement.MutiTaskLoopMachine(currentMachine, data["name"], data["params"]["mutiTask"]["loopMax"],  data["params"]["mutiTask"]["LoopConditionExpression"], False, data["targetName"])
                elif data["params"]["type"]["is_mutitask_loop"]:
                    xstateJSONElement.MutiTaskLoopMachine(currentMachine, data["name"], data["params"]["mutiTask"]["loopMax"], None, False, data["targetName"])
                elif data["params"]["type"]["is_mutitask_parallel"]:
                    xstateJSONElement.MutiTaskPallelMachine(currentMachine,data["name"], data["params"]["mutiTask"]["ParallelNum"], False, data["targetName"])
                else:
                    xstateJSONElement.singleMessageMachine(currentMachine, data["name"], data["targetName"],data["params"]["MessageGlobalVariable"] if len(data["params"]["MessageGlobalVariable"])>0 else None)
        case _:
            print("error")
            pass
           


def translate_bpmn2json(choreography_id,xml_string):
    choreography = Choreography()
    choreography.load_diagram_from_string(xml_string)
    
    method_to_extract_parallel_gateway(choreography)
    with open("res.json", 'r', encoding='utf-8') as file:
        tree = json.load(file)
    ParallelGateway_pairs = tree["parallel_gateway_pairs"]

    dataMap = get_element_machineInfo(choreography,ParallelGateway_pairs)

    xstateJSONElement = XstateJSONElement()
    xstateJSONElement.initMainMachine(choreography_id, dataMap["start_event"][0],dataMap["start_event"][1],dataMap["end_event"])
    xstateJSONElement.initGlobal(dataMap["globalVariable"])
    DFS_translate(tree, xstateJSONElement.mainMachine,dataMap,xstateJSONElement)

    return json.dumps(xstateJSONElement.mainMachine),json.dumps(xstateJSONElement.additionalContent)



    """with open("mainMachine.json", "w", encoding="utf-8") as f:
        json.dump(xstateJSONElement.mainMachine, f)
        
    with open("additionalContent.json", "w", encoding="utf-8") as f:
        json.dump(xstateJSONElement.additionalContent, f)"""
    
    






if __name__ == "__main__":
    # translate_bpmn2json("NewTest_paper","../bpmn_muti/supplypaper_new111.bpmn")

    translate_bpmn2json("NewTest_paper","../bpmn_muti/supplypaper_test2.bpmn")


    choreography = Choreography()
    choreography.load_diagram_from_xml_file("../bpmn_muti/supplypaper_new111.bpmn")
    """elements = choreography.query_element_with_type(NodeType.EXCLUSIVE_GATEWAY)
    set1 = set()
    for element in elements:
        for outgoing in element.outgoings:
            variables = extract_variable_names(outgoing.name)
            set1.update(variables)
    print(set1)"""

    """elements = choreography.query_element_with_type(NodeType.CHOREOGRAPHY_TASK)
    for element in elements:
        print(element.message_flows[0].message)"""



        # parsed_data = json.loads(element.documentation)
        # output_names = [output['name'] for output in parsed_data['outputs']]

    
    




