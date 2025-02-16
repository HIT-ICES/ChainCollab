from typing import Callable
import json
from parser import Choreography
from pprint import pprint
from copy import deepcopy
from elements import Element, NodeType

ident = 0


def format_print(*content):
    # print("  " * ident, *content)
    pass


def method_to_extract_parallel_gateway(choreography: Choreography):

    ParallelGatewayPairStrSet = set()
    def is_split_parallel_gateway(element):
        return element.type == NodeType.PARALLEL_GATEWAY and len(element.outgoings) > 1

    def is_merged_parallel_gateway(element):
        return element.type == NodeType.PARALLEL_GATEWAY and len(element.incomings) > 1

    def print_machine(machine):
        # 1. print the element of machine in order
        # 2. match if a nested machine is start with current element
        # 3. print the nested machine start with current element recursively

        global ident
        ident += 1
        for element in machine["direct_elements"]:
            format_print(element)
        for nested_machine in machine["nested_machines"]:
            print_machine(nested_machine)
        ident -= 1
        # Parallel Gateway

    def next_elements(source_element) -> list[Element]:
        if source_element.type == NodeType.END_EVENT:
            return []
        if source_element.type in (NodeType.PARALLEL_GATEWAY, NodeType.EXCLUSIVE_GATEWAY, NodeType.EVENT_BASED_GATEWAY):
            return [edge.target for edge in source_element.outgoings]
        if source_element.type in NodeType:
            return [source_element.outgoing.target]
        return []

    def init_blank_machine():
        return {
            "start_element": None,
            "end_element": None,
            "machine_name": "",
            "direct_elements": [],
            "nested_machines": [],
        }

    def single_path_logic(machine, start_element, stop_condition_func: Callable[[Element], bool]):
        cursor = start_element
        while not stop_condition_func(cursor):
            machine["direct_elements"].append(cursor.id)
            if cursor.type == NodeType.END_EVENT:
                break
            if cursor.type in [NodeType.EXCLUSIVE_GATEWAY, NodeType.EVENT_BASED_GATEWAY]:
                handle_exclusive_gateway(cursor, machine)
                break
            if is_split_parallel_gateway(cursor):
                inner_end_element = handle_parallel_gateway(cursor, machine)
                machine["direct_elements"].append(inner_end_element.id)
                cursor = next_elements(inner_end_element)[0]
                continue
            cursor = next_elements(cursor)[0]

    def handle_parallel_gateway(start_element, outer_machine) -> Element:
        global ident
        ident += 1

        # 0. scan all path
        # 1. Create a new machine for every path
        # 2. Add all the elements between the start_element and end_element to the new machine
        # 3. If there is a gateway in the middle, call this function recursively
        # 4. Add the new machine to the outer machine
        # 5. Return the end_element of the new machine
        def find_merged_parallel_gateway(start_element) -> Element:
            print("START ELEMENT", start_element.id)
            count = 1
            current_element = start_element
            while count != 0:
                current_element = next_elements(current_element)[0]  # always choose the first one to find the end
                if is_split_parallel_gateway(current_element):
                    count += 1
                if is_merged_parallel_gateway(current_element):
                    count -= 1
            end_element = current_element
            return end_element

        end_element = find_merged_parallel_gateway(start_element)

        ParallelGatewayPairStrSet.add(f"{start_element.id}_TO_{end_element.id}")

        format_print(f"START: handle elements between {start_element.id} and {end_element.id}")

        for idx, element in enumerate(next_elements(start_element)):
            # generate a new machine for every path
            new_machine = init_blank_machine()
            new_machine["start_element"] = start_element.id
            new_machine["machine_name"] = f"{start_element.id} to {end_element.id} path {idx}"
            cursor = element
            format_print("FOR", idx, element.id, "to", end_element.id)
            single_path_logic(new_machine, cursor, lambda x: x.id == end_element.id)
            new_machine["end_element"] = end_element.id
            outer_machine["nested_machines"].append(new_machine)

        format_print(f"END:handle elements between {start_element.id} and {end_element.id} ")

        ident -= 1
        return end_element

    def handle_exclusive_gateway(start_element, machine):
        for idx, element in enumerate(next_elements(start_element)):
            # no new machine is created
            single_path_logic(machine, element, lambda x: x.id in machine["direct_elements"])

    # main Procedure start

    start_element = choreography.query_element_with_type(NodeType.START_EVENT)[0]
    end_element = choreography.query_element_with_type(NodeType.END_EVENT)[0]

    machine = init_blank_machine()
    machine["start_element"] = start_element.id
    machine["machine_name"] = f"{start_element.id} to {end_element.id}"
    single_path_logic(machine, start_element, lambda x: False)
    machine["parallel_gateway_pairs"] = []
    machine["parallel_gateway_pairs"].extend(ParallelGatewayPairStrSet)
    
    with open("res.json", "w", encoding="utf-8") as f:
        json.dump(machine, f)
    # print_machine(machine)
    # pprint(machine)

    with open("res.json", "w", encoding="utf-8") as f:
        json.dump(machine, f)


if "__main__" == __name__:
    choreography = Choreography()
    choreography.load_diagram_from_xml_file("../bpmn_muti/supplypaper_new111.bpmn")
    res = method_to_extract_parallel_gateway(choreography)
