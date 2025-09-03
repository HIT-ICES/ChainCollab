# Construct a network of choreography from a given choreography file

import networkx as nx
import xml.etree.ElementTree as ET
import json


from elements import (
    NodeType,
    EdgeType,
    RootType,
    TaskLoopType,
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
    BusinessRuleTask,
)

from typing import List, Optional, Tuple, Any, Protocol
from protocals import ElementProtocol, GraphProtocol


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

    def query_edge_with_source_and_target(self, source_id, target_id):
        return [element for element in self.edges if element.source.id == source_id and element.target.id == target_id]

    def _parse_node(self, element: ET.Element):
        bpmn2prefix = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
        split_tag = element.tag.split("}")[1]
        match split_tag:
            case NodeType.PARTICIPANT.value:
                assert len(element.findall(f"./{bpmn2prefix}participantMultiplicity")) <= 1
                participant_multiplicity = element.findall(f"./{bpmn2prefix}participantMultiplicity")

                is_multi = False
                multi_maximum = 0
                multi_minimum = 0

                if participant_multiplicity:
                    is_multi = True
                    multi_maximum = int(participant_multiplicity[0].attrib.get("maximum", 0))
                    multi_minimum = int(participant_multiplicity[0].attrib.get("minimum", 0))

                return Participant(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    is_multi,
                    multi_minimum,
                    multi_maximum,
                )
            case NodeType.MESSAGE.value:
                documentation_list = element.findall(f"./{bpmn2prefix}documentation")
                documentation = documentation_list[0].text if documentation_list else None
                return Message(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    documentation=documentation if documentation is not None else "{}",
                )
            case NodeType.BUSINESS_RULE_TASK.value:
                # Parser Input & Output
                documentation_list = element.findall(f"./{bpmn2prefix}documentation")
                documentation = documentation_list[0].text if documentation_list else None
                return BusinessRuleTask(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    incoming=element.findall(f"./{bpmn2prefix}incoming")[0].text,
                    outgoing=element.findall(f"./{bpmn2prefix}outgoing")[0].text,
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
                is_multi = False
                loop_type = TaskLoopType.NONE
                loop_cardinality = 0
                completion_condition = ""
                if (the_type := element.attrib.get("loopType", "")) != "":
                    is_multi = True
                    loop_type = TaskLoopType(the_type)
                    loop_cardinality = int(element.attrib.get("loopCardinality", 0))
                    completion_condition = element.attrib.get("completionCondition", "")

                return ChoreographyTask(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    incoming=element.findall(f"./{bpmn2prefix}incoming")[0].text,
                    outgoing=element.findall(f"./{bpmn2prefix}outgoing")[0].text,
                    participants=[element.text for element in element.findall(f"./{bpmn2prefix}participantRef")],
                    message_flows=[element.text for element in element.findall(f"./{bpmn2prefix}messageFlowRef")],
                    init_participant=element.attrib.get("initiatingParticipantRef", ""),
                    is_multi=is_multi,
                    loop_type=loop_type,
                    loop_cardinality=loop_cardinality,
                    completion_condition=completion_condition,
                )
            case NodeType.EXCLUSIVE_GATEWAY.value:
                return ExclusiveGateway(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    incomings=[element.text for element in element.findall(f"./{bpmn2prefix}incoming")],
                    outgoings=[element.text for element in element.findall(f"./{bpmn2prefix}outgoing")],
                )
            case NodeType.PARALLEL_GATEWAY.value:
                return ParallelGateway(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    incomings=[element.text for element in element.findall(f"./{bpmn2prefix}incoming")],
                    outgoings=[element.text for element in element.findall(f"./{bpmn2prefix}outgoing")],
                )
            case NodeType.EVENT_BASED_GATEWAY.value:
                return EventBasedGateway(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    incomings=[element.text for element in element.findall(f"./{bpmn2prefix}incoming")],
                    outgoings=[element.text for element in element.findall(f"./{bpmn2prefix}outgoing")],
                )

    def _parse_edge(self, element):
        bpmn2prefix = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
        match element.tag.split("}")[1]:
            case EdgeType.MESSAGE_FLOW.value:
                self.message_to_add.append(element.attrib.get("messageRef"))
                # print(element.attrib["messageRef"])
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

    def _parse_messages(self, root):
        # Add Message to Graph base on demand of MessageFlow
        message_to_add = [
            element
            for element in root
            if element.tag.split("}")[1] == NodeType.MESSAGE.value
            and element.attrib.get("id", "") in self.message_to_add
        ]
        for message in message_to_add:
            message_node = self._parse_node(message)
            self.nodes.append(message_node)
            self._id2nodes[message_node.id] = message_node

    @property
    def simple_graph(self):
        # TODO : USE GRAPH TO EXECUTE SOME ALGORITHMS
        for node in self.nodes:
            self.graph.add_node(node.id, node=node)
        for edge in self.edges:
            self.graph.add_edge(edge.source.id, edge.target.id, edge=edge)

    @property
    def topology_graph_without_message(self):
        graph = nx.DiGraph()
        for node in self.nodes:
            if node.type == NodeType.MESSAGE or node.type == NodeType.PARTICIPANT:
                continue
            graph.add_node(node.id)
        for edge in self.edges:
            if edge.type == EdgeType.MESSAGE_FLOW:
                continue
            graph.add_edge(edge.source.id, edge.target.id, edge=edge)
        return graph

    def _init_element_properties(self):
        for node in self.nodes:
            node.deferred_init()
        for edge in self.edges:
            edge.deferred_init()

    def load_from_root(self, root, target=""):

        # if no target, load all, and if there are more than one, throw error

        target_elements = [
            element
            for element in root
            if element.tag.split("}")[1] == RootType.CHOREOGRAPHY.value
            and (target == "" or element.attrib.get("id", "") == target)
        ]
        if len(target_elements) != 1:
            # Parse Error! TODO
            print("Error: target not found or multiple targets found")
            return
        target_element = target_elements[0]
        self.message_to_add = []
        self._parse_element(target_element)
        self._parse_messages(root)
        self._init_element_properties()

    def load_diagram_from_xml_file(self, file_path, target=""):
        document = ET.parse(file_path, ET.XMLParser(encoding="utf-8"))
        root = document.getroot()
        self.load_from_root(root, target)

    def load_diagram_from_string(self, xml_string, target=""):
        root = ET.fromstring(xml_string)
        self.load_from_root(root, target)

    @property
    def simple_paths(self, start_id, end_id) -> list[NodeType]:
        return nx.all_simple_paths(self.topology_graph_without_message, start_id, end_id)

    @property
    def simple_paths_with_cycle(self, start_id, end_id):
        simple_paths = nx.all_simple_paths(self.topology_graph_without_message, start_id, end_id)

        cycles = list(nx.simple_cycles(self.topology_graph_without_message))
        paths_with_cycle = []
        for simple_path in simple_paths:
            for cycle in cycles:
                for index, step in enumerate(simple_path):
                    if cycle[0] == step:
                        path_with_cycle = simple_path.copy()[:index] + cycle + simple_path.copy()[index:]
                        paths_with_cycle.append(path_with_cycle)

        all_paths = simple_paths + paths_with_cycle
        return all_paths
