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
    

    if element.type==NodeType.END_EVENT:
        return element.id
    
    if element.type==NodeType.START_EVENT:
        return {element.id:element.outgoing.target.id}

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

    businessRules = choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK)
    for element in businessRules:
        dataMap[element.id] = extract_element_info(element)

    ParallelGateways = choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY)
    for element in ParallelGateways:
        dataMap["parallelGateway_next"][element.id] = extract_element_info(element)

    

    endEvents = choreography.query_element_with_type(NodeType.END_EVENT)
    for element in endEvents:
        dataMap["end_event"].append(extract_element_info(element))

    startEvent = choreography.query_element_with_type(NodeType.START_EVENT)[0]
    dataMap["start_event"] = extract_element_info(startEvent)
    



    for key, data in dataMap.items():
        print({key: data})
    
    return dataMap


def DFS_translate(tree, currentMachine,dataMap,name,endName,xstateJSONElement):
    if "Fixed" in name:
        currentMachine["type"] = "parallel"
        xstateJSONElement.SetOndone(currentMachine,dataMap["parallelGateway_next"][endName])

    for node in tree["direct_elements"]:
        if node in dataMap.keys():
            addMachine(currentMachine, dataMap[node],xstateJSONElement)

    for branch in tree["nested_machines"]:
        childrenName = "Fixed_"+branch["start_element"]+"_TO_"+ branch["end_element"]       
        DFS_translate(branch, currentMachine["states"][childrenName], dataMap,childrenName,branch["end_element"],xstateJSONElement)
   
        
def addMachine(currentMachine, data,xstateJSONElement):
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
                    xstateJSONElement.singleMessageMachine(currentMachine, data["name"], data["targetName"])
        case _:
            print("error")
            pass
           


def translate_bpmn2json(choreography_id,file):
    choreography = Choreography()
    choreography.load_diagram_from_xml_file(file)
    dataMap = get_element_machineInfo(choreography)
    tree = method_to_extract_parallel_gateway(choreography)
    xstateJSONElement = XstateJSONElement()
    xstateJSONElement.initMainMachine(choreography_id, dataMap["start_event"].keys()[0],dataMap["start_event"][dataMap["start_event"].keys()[0]],dataMap["end_event"])
    DFS_translate(tree, xstateJSONElement.mainMachine,dataMap,choreography_id,None,xstateJSONElement)

    print(xstateJSONElement.additionalContent)
    print(xstateJSONElement.mainMachine)
    


if __name__ == "__main__":
    translate_bpmn2json("Choreography_hsdkfjhk","../bpmn_muti/Blood_analysis.bpmn")





    """
    choreography = Choreography()
    choreography.load_diagram_from_xml_file("../bpmn_muti/Blood_analysis.bpmn")
    element = choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY)[0]
    print(element.outgoings[1].id)
    data={
        "sss":1
    }
    print("sss" in data.keys())
    """
