'''
1.提取所有元素的重要信息,并使用写好的Parallel算法处理成层次结构
    {
        "name":None,
        "targetNames":[],
        "type":None,
        "params":{
            "aaa":None,
            #根据类型填入信息
            #1.mutiParicipant特殊信息:max, isFirstTime,participantName<---需要算法识别出首次   
            #2.mutiTask特殊信息:loopMax,LoopConditionExpression,[isMutiParticipant=False,MutiParticipantParam={}]
            #3.DMN特殊信息:DMNOutputNameList
        }
    }
   
2.根据 
     1.层次结构
     2.每个元素的类型 
  来递归添加状态机json

'''


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
        "params": {}
    }
    if element.type==NodeType.PARALLEL_GATEWAY or element.type==NodeType.EXCLUSIVE_GATEWAY or element.type==NodeType.EVENT_BASED_GATEWAY:
        metaData["targetName"] =[edge.target.id for edge in element.outgoings] 
    elif element.type==NodeType.END_EVENT:
        metaData["targetName"] =None
    else:
        metaData["targetName"] = element.outgoing.target.id

    #TODO:根据类型填入信息

    return metaData


def get_element_machineInfo(choreography:Choreography):
    
    dataMap = {}

    choreographyTasks = choreography.query_element_with_type(NodeType.CHOREOGRAPHY_TASK)
    for element in choreographyTasks:
        dataMap[element.id] = extract_element_info(element)
        # TODO:
    
    parallelGateways = choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY)
    ExclusiveGateways = choreography.query_element_with_type(NodeType.EXCLUSIVE_GATEWAY)
    EventBasedGateways = choreography.query_element_with_type(NodeType.EVENT_BASED_GATEWAY)
    for element in parallelGateways:
        print(element.type.value)
        dataMap[element.id] = extract_element_info(element)
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


    
    for key, data in dataMap.items():
        print({key: data})
    
    return dataMap


def DFS_translate(tree, currentMachine,dataMap,mainMachine,addtionalContent,name,xstateJSONElement):
    if "Gateway" in name:
        currentMachine["type"] = "parallel"
    for node,children in tree.items():
        if children:
            DFS_translate(children, currentMachine["states"]["children"], dataMap,mainMachine,addtionalContent,xstateJSONElement)
            return
        addMachine(currentMachine, dataMap[node],mainMachine,addtionalContent,xstateJSONElement)
    
        
def addMachine(currentMachine, dataMap,mainMachine,addtionalContent,xstateJSONElement):
    match dataMap["type"]:
        case NodeType.EXCLUSIVE_GATEWAY.value:
            xstateJSONElement.ExclusiveGatewayMachine()
        case NodeType.EVENT_BASED_GATEWAY.value:
            xstateJSONElement.EventGatewayMachine()
        case NodeType.BUSINESS_RULE_TASK.value:
            xstateJSONElement.DMNMachine()

        #TODO:
        case NodeType.CHOREOGRAPHY_TASK.value:
            pass



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
    translate_bpmn2json()