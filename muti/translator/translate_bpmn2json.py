'''
1.提取所有元素

'''


from snippet.snippet_1 import XstateJSONElement

from translator.parser import Choreography
from pprint import pprint
from copy import deepcopy
from translator.elements import (
    Element,
    StartEvent,
    ParallelGateway,
    ExclusiveGateway,
    EventBasedGateway,
    NodeType,
    EdgeType,
    EndEvent,
)





def translate_bpmn2json(bpmn):
    choreography = Choreography()
    choreography.load_diagram_from_xml_file("./bpmn_muti/parallel.bpmn")
    message = choreography.query_element_with_type(NodeType.MESSAGE)[0]
    print(message)
    xstateJSONElement = XstateJSONElement()
    xstateJSONElement.initMachine
    # xstateJSONElement.singleMessageMachine()

