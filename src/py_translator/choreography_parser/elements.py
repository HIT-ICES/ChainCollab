# Define all Choreographt Elements Here

# Type Enum

from enum import Enum
from typing import List, Optional, Tuple, Any, Protocol
from .protocals import ElementProtocol, GraphProtocol


class NodeType(Enum):
    PARTICIPANT = "participant"
    MESSAGE = "message"
    START_EVENT = "startEvent"
    END_EVENT = "endEvent"
    CHOREOGRAPHY_TASK = "choreographyTask"
    EXCLUSIVE_GATEWAY = "exclusiveGateway"
    PARALLEL_GATEWAY = "parallelGateway"
    EVENT_BASED_GATEWAY = "eventBasedGateway"
    BUSINESS_RULE_TASK = "businessRuleTask"


class EdgeType(Enum):
    MESSAGE_FLOW = "messageFlow"
    SEQUENCE_FLOW = "sequenceFlow"


class TerminalType(Enum):
    BPMNDiagram = "BPMNDiagram"


class PropertyMeta(type):
    def __new__(cls, name, bases, attrs):
        _object_properties = attrs.get("_object_properties", [])
        for attr_name in attrs.get("_properties", []):
            if attr_name in _object_properties:

                def getter(self, attr_name=attr_name) -> Optional[List["Element"]]:
                    if isinstance(getattr(self, "_" + attr_name), list):
                        return [
                            attr["element"] for attr in getattr(self, "_" + attr_name)
                        ]
                    else:
                        return getattr(self, "_" + attr_name)["element"]

            else:

                def getter(self, attr_name=attr_name) -> str:  # type: ignore
                    return getattr(self, "_" + attr_name)

            attrs[attr_name] = property(getter)
        return super().__new__(cls, name, bases, attrs)


class Element(metaclass=PropertyMeta):
    _properties: List[str] = ["id", "name", "type"]
    _object_properties: List[str] = []
    _type: str = "element"  # type: ignore

    def __init__(self, graph: GraphProtocol, id: str, name: str = ""):
        self._id: str = id
        self._graph: GraphProtocol = graph
        self._name: str = name

    def deferred_init(self) -> None:
        for attr in self._object_properties:
            if isinstance(getattr(self, "_" + attr), list):
                setattr(
                    self,
                    "_" + attr,
                    [
                        {
                            "id": inner_attr["id"],
                            "element": self._graph.get_element_with_id(
                                inner_attr["id"]
                            ),
                        }
                        for inner_attr in getattr(self, "_" + attr)
                    ],
                )
                continue
            setattr(
                self,
                "_" + attr,
                {
                    "id": getattr(self, "_" + attr)["id"],
                    "element": self._graph.get_element_with_id(
                        getattr(self, "_" + attr)["id"]
                    ),
                },
            )


def initObjectProperties(id: str) -> dict:
    return {"id": id, "element": None}


# Node Types


class Participant(Element):
    _type: NodeType = NodeType.PARTICIPANT
    _properties: List[str] = [
        "id",
        "name",
        "type",
        "is_multi",
        "multi_minimum",
        "multi_maximum",
    ]
    _object_properties: List[str] = []

    def __init__(self, graph, id: str, name: str = "", is_multi: bool = False,  multi_minimum: int = 0, multi_maximum: int = 0):
        super().__init__(graph, id, name)
        self._is_multi: bool = is_multi
        self._multi_minimum: int = multi_minimum
        self._multi_maximum: int = multi_maximum


class Message(Element):
    _type: NodeType = NodeType.MESSAGE
    _properties: List[str] = ["id", "name", "type", "documentation"]
    _object_properties: List[str] = []

    def __init__(self, graph, id: str, name: str = "", documentation: str = ""):
        super().__init__(graph, id)
        self._name: str = name
        self._documentation: str = documentation


class StartEvent(Element):
    _type: NodeType = NodeType.START_EVENT
    _properties: List[str] = ["id", "name", "type", "outgoing"]
    _object_properties: List[str] = ["outgoing"]

    def __init__(self, graph, id: str, name: str = "", outgoing: str = ""):
        super().__init__(graph, id, name)
        self._outgoing: dict = initObjectProperties(outgoing)


class EndEvent(Element):
    _type: NodeType = NodeType.END_EVENT
    _properties: List[str] = ["id", "name", "type", "incoming"]
    _object_properties: List[str] = ["incoming"]

    def __init__(self, graph, id: str, name: str = "", incoming: str = ""):
        super().__init__(graph, id, name)
        self._incoming: dict = initObjectProperties(incoming)


class ChoreographyTask(Element):
    _type: NodeType = NodeType.CHOREOGRAPHY_TASK
    _properties: List[str] = [
        "id",
        "name",
        "type",
        "incoming",
        "outgoing",
        "participants",
        "init_participant",
        "message_flows",
    ]
    _object_properties: List[str] = [
        "incoming",
        "outgoing",
        "participants",
        "init_participant",
        "message_flows",
    ]

    def __init__(
        self,
        graph,
        id: str,
        name: str = "",
        incoming: str = "",
        outgoing: str = "",
        participants: Tuple[str, ...] = (),
        init_participant: str = "",
        message_flows: Tuple[str, ...] = (),
    ):
        super().__init__(graph, id, name)
        self._incoming: dict = initObjectProperties(incoming)
        self._outgoing: dict = initObjectProperties(outgoing)
        self._participants: List[dict] = [
            initObjectProperties(participant) for participant in participants
        ]
        self._init_participant: dict = initObjectProperties(init_participant)
        self._message_flows: List[dict] = [
            initObjectProperties(message_flow) for message_flow in message_flows
        ]

    @property
    def init_message_flow(self):
        for message_flow in self.message_flows:
            if message_flow.source == self.init_participant:
                return message_flow
        return None

    @property
    def return_message_flow(self):
        for message_flow in self.message_flows:
            if message_flow.target == self.init_participant:
                return message_flow
        return None


class ExclusiveGateway(Element):
    _type: NodeType = NodeType.EXCLUSIVE_GATEWAY
    _properties: List[str] = ["id", "name", "type", "incomings", "outgoings"]
    _object_properties: List[str] = ["incomings", "outgoings"]

    def __init__(
        self,
        graph,
        id: str,
        name: str = "",
        incomings: Tuple[str, ...] = (),
        outgoings: Tuple[str, ...] = (),
    ):
        super().__init__(graph, id, name)
        self._incomings: List[dict] = [
            initObjectProperties(incoming) for incoming in incomings
        ]
        self._outgoings: List[dict] = [
            initObjectProperties(outgoing) for outgoing in outgoings
        ]


class ParallelGateway(Element):
    _type: NodeType = NodeType.PARALLEL_GATEWAY
    _properties: List[str] = ["id", "name", "type", "incomings", "outgoings"]
    _object_properties: List[str] = ["incomings", "outgoings"]

    def __init__(
        self,
        graph,
        id: str,
        name: str = "",
        incomings: Tuple[str, ...] = (),
        outgoings: Tuple[str, ...] = (),
    ):
        super().__init__(graph, id, name)
        self._incomings: List[dict] = [
            initObjectProperties(incoming) for incoming in incomings
        ]
        self._outgoings: List[dict] = [
            initObjectProperties(outgoing) for outgoing in outgoings
        ]


class EventBasedGateway(Element):
    _type: NodeType = NodeType.EVENT_BASED_GATEWAY
    _properties: List[str] = ["id", "name", "type", "incomings", "outgoings"]
    _object_properties: List[str] = ["incomings", "outgoings"]

    def __init__(
        self,
        graph,
        id: str,
        name: str = "",
        incomings: Tuple[str, ...] = (),
        outgoings: Tuple[str, ...] = (),
    ):
        super().__init__(graph, id, name)
        self._incomings: List[dict] = [
            initObjectProperties(incoming) for incoming in incomings
        ]
        self._outgoings: List[dict] = [
            initObjectProperties(outgoing) for outgoing in outgoings
        ]


class BusinessRuleTask(Element):
    _type: NodeType = NodeType.BUSINESS_RULE_TASK
    _properties: List[str] = ["id", "name", "type", "incoming", "outgoing"]
    _object_properties: List[str] = ["incoming", "outgoing"]

    def __init__(self, graph, id: str, name: str = "", incoming: str = "", outgoing: str = ""):
        super().__init__(graph, id, name)
        self._incoming: dict = initObjectProperties(incoming)
        self._outgoing: dict = initObjectProperties(outgoing)


# Edge Types


class MessageFlow(Element):
    _type: EdgeType = EdgeType.MESSAGE_FLOW
    _object_properties: List[str] = ["source", "target", "message"]
    _properties: List[str] = ["id", "name", "type", "source", "target", "message"]

    def __init__(
        self,
        graph,
        id: str,
        name: str = "",
        source: str = "",
        target: str = "",
        message: str = "",
    ):
        super().__init__(graph, id, name)
        self._source: dict = initObjectProperties(source)
        self._target: dict = initObjectProperties(target)
        self._message: dict = initObjectProperties(message)


class SequenceFlow(Element):
    _type: EdgeType = EdgeType.SEQUENCE_FLOW
    _object_properties: List[str] = ["source", "target"]
    _properties: List[str] = ["id", "name", "type", "source", "target"]

    def __init__(
        self,
        graph,
        id: str,
        name: str = "",
        source: str = "",
        target: str = "",
    ):
        super().__init__(graph, id, name)
        self._source: dict = initObjectProperties(source)
        self._target: dict = initObjectProperties(target)
