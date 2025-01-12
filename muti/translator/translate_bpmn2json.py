'''
1.提取所有元素的重要信息,并使用写好的Parallel算法处理成层次结构
    {
        "name":None,
        "targetNames":[],
        "type":None,
        "params":{
            "aaa":None,
            #根据类型填入信息
            #1.mutiParicipant特殊信息:max, isFirstTime<---需要算法识别出首次   
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
    EndEvent,
)





def translate_bpmn2json():
    choreography = Choreography()
    choreography.load_diagram_from_xml_file("../bpmn_muti/Purchase_new2.bpmn")
    a = choreography.query_element_with_type(NodeType.CHOREOGRAPHY_TASK)[0]
    print(a.outgoing.target.id)
    xstateJSONElement = XstateJSONElement()
    # xstateJSONElement.singleMessageMachine()
    {
        "name":None,
        "targetNames":[],
        "type":None,
        "params":{
            "aaa":None,
            #根据类型填入信息
            #1.mutiParicipant特殊信息:max, isFirstTime<---需要算法识别出首次   
            #2.mutiTask特殊信息：loopMax,LoopConditionExpression,[isMutiParticipant=False,MutiParticipantParam={}]
            #3.DMN特殊信息：DMNOutputNameList
        }
    }


translate_bpmn2json()