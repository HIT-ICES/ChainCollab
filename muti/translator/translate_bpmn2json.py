'''
1.提取所有元素的重要信息,并使用写好的Parallel算法处理成层次结构
    {
        "name":None,
        "targetName":None,
        "type":None,
        "params":{
            "mutiParticipant":{
                "max":3,
                "mutiparticipantName":"aaa",
            }
            "mutiTask":{
                "loopMax":3,
                "LoopConditionExpression":"aaa",
                "ParallelNum":3
            }
            "DMN":{
                "DMNOutputNameList":[]
            }
            "ExclusiveGateway":{
                "targetList":[
                    {
                        "targetName":"aaa",
                        "condition":"aaa"
                    }
                ]
            }
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
   
2.根据 
     1.层次结构
     2.每个元素的类型 
  来递归添加状态机json




  exlusiveGateway      的   condition
  dmn                  的   dmnOutputNameList 应该要document提取? 
  mutiTask_顺序多实例   的   loop_max 
  mutiTask_带跳出循环   的   loop_condition
  mutiTask_并行多实例   的   parallel_num
  
  eventGateway的event怎么表示? 后续给状态机发送一条边的id?

'''


from enum import Enum
from snippet_1 import XstateJSONElement

from parser import Choreography
from pprint import pprint
from copy import deepcopy
from elements import (
    Element,
    StartEvent,
    ParallelGateway,
    ExclusiveGateway,
    EventBasedGateway,
    NodeType,
    EdgeType,
    EndEvent
)
from ParallelGateway import method_to_extract_parallel_gateway



def extract_element_info(element: Element):
    metaData = {
        "type": element.type.value,
        "name": element.id,
        "targetName": None,
        "params": {
            "type":{
                "is_mutiparticipant":False,
                "is_mutitask_loop":False,
                "is_mutitask_loop_condition":False,
                "is_mutitask_parallel":False
            }
        }
    }
    if element.type==NodeType.END_EVENT or element.type==NodeType.PARALLEL_GATEWAY or element.type==NodeType.EXCLUSIVE_GATEWAY or element.type==NodeType.EVENT_BASED_GATEWAY:
        metaData["targetName"] =None
    else:
        metaData["targetName"] = element.outgoing.target.id
    

    #处理排他网关
    if element.type==NodeType.EXCLUSIVE_GATEWAY:
        metaData["params"]["ExclusiveGateway"]["targetList"] = [{"targetName":edge.target.id,"condition":"edge.condition"} for edge in element.outgoings]
        return metaData

    #处理事件网关
    if element.type==NodeType.EXCLUSIVE_GATEWAY:
        metaData["params"]["EventGateway"]["targetList"] = [{"targetName":edge.target.id,"event":edge.id} for edge in element.outgoings]
        return metaData
    #处理DMN
    if element.type==NodeType.BUSINESS_RULE_TASK:
        metaData["params"]["DMN"]["DMNOutputNameList"] = "element.dmnOutputNameList"
        return metaData
    
    if element.type==NodeType.PARALLEL_GATEWAY:
        return element.outgoings[0].target.id

    #处理task
    if element.type==NodeType.CHOREOGRAPHY_TASK:
        metaData["type"] = "message"
        if hasattr(element,"loop_max"):
            metaData["params"]["mutiTask"]["loopMax"] = element.loop_max
            metaData["params"]["type"]["is_mutitask_loop"] = True
            if hasattr(element,"loop_condition"):
                metaData["params"]["mutiTask"]["LoopConditionExpression"] = element.loop_condition
                metaData["params"]["type"]["is_mutitask_loop_condition"] = True
        elif hasattr(element,"parallel_num"):
            metaData["params"]["mutiTask"]["ParallelNum"] = element.parallel_num
            metaData["params"]["type"]["is_mutitask_parallel"] = True
        
        metaData1 = deepcopy(metaData)
        metaData2 = deepcopy(metaData)

        if element.init_participant.id == element.message_flows[0].source.id:
            metaData1["name"] = element.message_flows[0].message.id
            metaData2["name"] = element.message_flows[1].message.id
        else:
            metaData1["name"] = element.message_flows[1].message.id
            metaData2["name"] = element.message_flows[0].message.id

        if hasattr(element,"participants"):
            #未考虑双muti
            if element.participants[0].is_multi:
                metaData1["params"]["mutiParticipant"]["max"] = element.participants[0].multi_maximum
                metaData1["params"]["mutiParticipant"]["mutiparticipantName"] = element.participants[0].multi_maximum
                metaData1["params"]["type"]["is_mutiparticipant"] = True
                metaData2["params"]["mutiParticipant"]["max"] = element.participants[0].multi_maximum
                metaData2["params"]["mutiParticipant"]["mutiparticipantName"] = element.participants[0].multi_maximum
                metaData2["params"]["type"]["is_mutiparticipant"] = True
            if element.participants[1].is_multi:
                metaData1["params"]["mutiParticipant"]["max"] = element.participants[1].multi_maximum
                metaData1["params"]["mutiParticipant"]["mutiparticipantName"] = element.participants[1].multi_maximum
                metaData1["params"]["type"]["is_mutiparticipant"] = True
                metaData2["params"]["mutiParticipant"]["max"] = element.participants[1].multi_maximum
                metaData2["params"]["mutiParticipant"]["mutiparticipantName"] = element.participants[1].multi_maximum
                metaData2["params"]["type"]["is_mutiparticipant"] = True

        return [metaData1,metaData2]

        


    


    #TODO:根据类型填入信息

    return metaData


def get_element_machineInfo(choreography:Choreography):
    
    dataMap = {}

    choreographyTasks = choreography.query_element_with_type(NodeType.CHOREOGRAPHY_TASK)
    for element in choreographyTasks:
        ordered_messages = extract_element_info(element)
        dataMap[element.id] = ordered_messages
    
    ExclusiveGateways = choreography.query_element_with_type(NodeType.EXCLUSIVE_GATEWAY)
    EventBasedGateways = choreography.query_element_with_type(NodeType.EVENT_BASED_GATEWAY)
    for element in ExclusiveGateways:
        dataMap[element.id] = extract_element_info(element)
    for element in EventBasedGateways:
        dataMap[element.id] = extract_element_info(element)

    endEvents = choreography.query_element_with_type(NodeType.END_EVENT)
    for element in endEvents:
        dataMap[element.id] = extract_element_info(element)

    startEvent = choreography.query_element_with_type(NodeType.START_EVENT)[0]
    dataMap[startEvent.id] = extract_element_info(startEvent)

    businessRules = choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK)
    for element in businessRules:
        dataMap[element.id] = extract_element_info(element)

    ParallelGateways = choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY)
    for element in ExclusiveGateways:
        dataMap["_next"][element.id] = extract_element_info(element)
    



    for key, data in dataMap.items():
        print({key: data})
    
    return dataMap


def DFS_translate(tree, currentMachine,dataMap,mainMachine,addtionalContent,name,endName,xstateJSONElement):

    if "Fixed" in name:
        currentMachine["type"] = "parallel"
        xstateJSONElement.SetOndone(currentMachine,dataMap["_next"][endName])

    for node in tree["direct_elements"]:
        if node in dataMap.keys():
            addMachine(currentMachine, dataMap[node],mainMachine,addtionalContent,xstateJSONElement)

    for branch in tree["nested_machines"]:
        childrenName = "Fixed_"+branch["start_element"]+"_TO_"+ branch["end_element"]       
        DFS_translate(branch, currentMachine["states"][childrenName], dataMap,mainMachine,addtionalContent,childrenName,branch["end_element"],xstateJSONElement)
   
        
def addMachine(currentMachine, data,mainMachine,addtionalContent,xstateJSONElement):
    match data["type"]:
        case NodeType.EXCLUSIVE_GATEWAY.value:
            xstateJSONElement.ExclusiveGatewayMachine(currentMachine,data["params"]["ExclusiveGateway"]["targetList"],data["name"])
        case NodeType.EVENT_BASED_GATEWAY.value:
            xstateJSONElement.EventGatewayMachine(currentMachine,data["params"]["EventGateway"]["targetList"],data["name"])
        case NodeType.BUSINESS_RULE_TASK.value:
            xstateJSONElement.DMNMachine(currentMachine,data["name"],["result1"],data["targetName"]) #暂时一个output
        case NodeType.CHOREOGRAPHY_TASK.value:
            if data["params"]["type"]["is_mutiparticipant"]:
                if data["params"]["type"]["is_mutitask_loop_condition"]:
                    xstateJSONElement
                elif data["params"]["type"]["is_mutitask_loop"]:
                    xstateJSONElement
                elif data["params"]["type"]["is_mutitask_parallel"]:
                    xstateJSONElement
                else:
                    xstateJSONElement
            else:
                if data["params"]["type"]["is_mutitask_loop_condition"]:
                    xstateJSONElement
                elif data["params"]["type"]["is_mutitask_loop"]:
                    xstateJSONElement
                elif data["params"]["type"]["is_mutitask_parallel"]:
                    xstateJSONElement
                else:
                    xstateJSONElement
        case _:
            pass
           


def translate_bpmn2json():
    choreography = Choreography()
    choreography.load_diagram_from_xml_file("../bpmn_muti/Blood_analysis.bpmn")
    dataMap = get_element_machineInfo(choreography)
    tree = method_to_extract_parallel_gateway(choreography)
    xstateJSONElement = XstateJSONElement()

    # TODO:
    xstateJSONElement.initMainMachine()
    DFS_translate()

    print(xstateJSONElement.additionalContent)
    print(xstateJSONElement.mainMachine)
    
   



if __name__ == "__main__":
    # translate_bpmn2json()

    choreography = Choreography()
    choreography.load_diagram_from_xml_file("../bpmn_muti/Blood_analysis.bpmn")

    element = choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY)[0]
    print(element.outgoings[1].id)


    data={
        "sss":1
    }
    print("sss" in data.keys())

    if "sss" in data.keys():
        print("AA")
    {
        "startevent":None,
        "ParallelGateway1 TO ParallelGateway2":{
            "task1(message下同) TO task2":{
                "task1":None,
                "task2":None,
            },
            "task1 TO task2":{
                "task3":None,
                "task4":None
            }
        },
        "task5":None,
        "DMN1":None,
        "ExclusiveGateway1":None,
        "task6":None,
        "endevent":None
    }