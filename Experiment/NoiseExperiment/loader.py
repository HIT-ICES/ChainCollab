from enum import Enum

from collections import namedtuple
from typing import NamedTuple


class BoolWithMessage(NamedTuple):
    value: bool
    message: str

    def __bool__(self):
        return self.value

    def __str__(self):
        return self.message


class ElementTypes(Enum):
    MESSAGE = "Message"
    GATEWAY = "Gateway"
    EVENT = "Event"
    ACTIVITY = "Activity"


class FormatType(Enum):
    JSON = "json"
    CSV = "csv"
    XML = "xml"


class STEP(NamedTuple):
    element: str
    type: ElementTypes
    param: list
    meta: str
    invoker: str
    check_conditions: list


class CHECK_CONDITION(NamedTuple):
    element: str
    element_type: ElementTypes
    pre_state: str
    post_state: str


class Task(NamedTuple):
    name: str
    steps: list[STEP]
    invoke_path: list


"""
{
    "name": "random-1",
    "steps": [
        {
            "element_name": "",
            "element_type": "random",
            "metaInfo": "",
            "parameters": [],
            "invoker": "",
            "check_condition": [
                {
                    "element_name": "random-1",
                    "element_type": "random",
                    "pre_state": "enable",
                    "post_state": "disable"
                }
            ]
        }
    ],
    "invoke_path": [
        "",
        ""
    ]
}
"""


def type_checker(type_name: str) -> ElementTypes:
    if "Message" == type_name:
        return ElementTypes.MESSAGE
    elif "Gateway" == type_name:
        return ElementTypes.GATEWAY
    elif "Event" == type_name:
        return ElementTypes.EVENT
    elif "Activity" == type_name:
        return ElementTypes.ACTIVITY


import json


def state_checker(state: str) -> str:
    match state:
        case "enable":
            return "ENABLED"
        case "disable":
            return "DISABLED"
        case "done":
            return "COMPLETED"


def step_loader(file_name: str) -> list:
    content = json.load(open(file_name, "r"))
    # name, steps, invoke_path
    task = Task(
        name=content["name"],
        steps=[
            STEP(
                element["element_name"],
                type_checker(element["element_type"]),
                element["parameters"],
                element["metaInfo"],
                element["invoker"],
                [
                    CHECK_CONDITION(
                        condition["element_name"],
                        type_checker(condition["element_type"]),
                        state_checker(condition["pre_state"]),
                        state_checker(condition["post_state"]),
                    )
                    for condition in element["state_change"]
                ],
            )
            for element in content["steps"]
        ],
        invoke_path=content["invoke_path"],
    )
    return task
