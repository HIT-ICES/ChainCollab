# Construct a network of choreography from a given choreography file

import networkx as nx
import xml.etree.ElementTree as ET

from .elements import (
    NodeType,
    EdgeType,
    Participant,
    Message,
    StartEvent,
    EndEvent,
    ChoreographyTask,
    ExclusiveGateway,
    ParallelGateway,
    EventBasedGateway,
    MessageFlow,
    SequenceFlow,
    TerminalType,
)

from typing import List, Optional, Tuple, Any, Protocol
from .protocals import ElementProtocol, GraphProtocol


class Choreography:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: List[ElementProtocol] = []
        self.edges: List[ElementProtocol] = []
        self._id2nodes = {}
        self._id2edges = {}

    def get_element_with_id(self, element_id):
        # node or edge
        return self._id2nodes.get(element_id, self._id2edges.get(element_id, None))

    def query_element_with_type(self, element_type):
        return [element for element in self.nodes if element.type == element_type] + [
            element for element in self.edges if element.type == element_type
        ]

    def _parse_node(self, element):
        bpmn2prefix = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
        split_tag = element.tag.split("}")[1]
        match split_tag:
            case NodeType.PARTICIPANT.value:
                return Participant(
                    self, element.attrib["id"], element.attrib.get("name", "")
                )
            case NodeType.MESSAGE.value:
                documentation_list = element.findall(f"./{bpmn2prefix}documentation")
                documentation = (
                    documentation_list[0].text if documentation_list else None
                )
                return Message(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    documentation=documentation if documentation is not None else "{}",
                )
            case NodeType.START_EVENT.value:
                return StartEvent(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    outgoing=element.findall(f"./{bpmn2prefix}outgoing")[0].text,
                )
            case NodeType.END_EVENT.value:
                return EndEvent(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    incoming=element.findall(f"./{bpmn2prefix}incoming")[0].text,
                )
            case NodeType.CHOREOGRAPHY_TASK.value:
                return ChoreographyTask(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    incoming=element.findall(f"./{bpmn2prefix}incoming")[0].text,
                    outgoing=element.findall(f"./{bpmn2prefix}outgoing")[0].text,
                    participants=[
                        element.text
                        for element in element.findall(f"./{bpmn2prefix}participantRef")
                    ],
                    message_flows=[
                        element.text
                        for element in element.findall(f"./{bpmn2prefix}messageFlowRef")
                    ],
                    init_participant=element.attrib.get("initiatingParticipantRef", ""),
                )
            case NodeType.EXCLUSIVE_GATEWAY.value:
                return ExclusiveGateway(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    incomings=[
                        element.text
                        for element in element.findall(f"./{bpmn2prefix}incoming")
                    ],
                    outgoings=[
                        element.text
                        for element in element.findall(f"./{bpmn2prefix}outgoing")
                    ],
                )
            case NodeType.PARALLEL_GATEWAY.value:
                return ParallelGateway(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    incomings=[
                        element.text
                        for element in element.findall(f"./{bpmn2prefix}incoming")
                    ],
                    outgoings=[
                        element.text
                        for element in element.findall(f"./{bpmn2prefix}outgoing")
                    ],
                )
            case NodeType.EVENT_BASED_GATEWAY.value:
                return EventBasedGateway(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    incomings=[
                        element.text
                        for element in element.findall(f"./{bpmn2prefix}incoming")
                    ],
                    outgoings=[
                        element.text
                        for element in element.findall(f"./{bpmn2prefix}outgoing")
                    ],
                )

    def _parse_edge(self, element):
        bpmn2prefix = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
        match element.tag.split("}")[1]:
            case EdgeType.MESSAGE_FLOW.value:
                return MessageFlow(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    element.attrib["sourceRef"],
                    element.attrib["targetRef"],
                    element.attrib.get("messageRef"),
                )

            case EdgeType.SEQUENCE_FLOW.value:
                return SequenceFlow(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    element.attrib["sourceRef"],
                    element.attrib["targetRef"],
                )

    def _parse_element(self, element):
        split_tag = element.tag.split("}")[1]
        if split_tag in [member.value for member in TerminalType.__members__.values()]:
            return
        if split_tag in [member.value for member in NodeType.__members__.values()]:
            self.nodes.append(self._parse_node(element))
            self._id2nodes[self.nodes[-1].id] = self.nodes[-1]
            return
        if split_tag in [member.value for member in EdgeType.__members__.values()]:
            self.edges.append(self._parse_edge(element))
            self._id2edges[self.edges[-1].id] = self.edges[-1]
            return
        # recursively parse the children of the element
        for child in element:
            self._parse_element(child)

    def _init_graph(self):
        for node in self.nodes:
            self.graph.add_node(node.id, node=node)
        for edge in self.edges:
            self.graph.add_edge(edge.sourceRef, edge.targetRef, edge=edge)

    def _init_element_properties(self):
        for node in self.nodes:
            node.deferred_init()
        for edge in self.edges:
            edge.deferred_init()

    def load_diagram_from_xml_file(self, file_path):
        document = ET.parse(file_path)
        root = document.getroot()
        # throught all the document, get all the elements, split as nodes and edges by their type(tag)
        for element in root:
            self._parse_element(element)
        self._init_element_properties()


if __name__ == "__main__":
    choreography = Choreography()
    choreography.load_diagram_from_xml_file("Coffee_machine.bpmn")

    start = choreography.query_element_with_type(NodeType.START_EVENT)[0]
    print(start.outgoing.target.id)
