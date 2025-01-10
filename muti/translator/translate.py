import json
from translator.parser import Choreography
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

ident = 0

def print():
    pass



def method_to_extract_parallel_gateway(choreography: Choreography):
    def is_split_parallel_gateway(element):
        return element.type == NodeType.PARALLEL_GATEWAY and len(element.outgoings) > 1

    def is_merged_parallel_gateway(element):
        return element.type == NodeType.PARALLEL_GATEWAY and len(element.incomings) > 1

    def print_machine(machine):
        # 1. print the element of machine in order
        # 2. match if a nested machine is start with current element
        # 3. print the nested machine start with current element recursively

        for element in machine["direct_elements"]:
            print(element)
            if element in machine["nested_machines"]:
                print_machine(machine["nested_machines"][element])

        # Parallel Gateway

    def next_elements(source_element) -> list[Element]:
        if source_element.type == NodeType.END_EVENT:
            return []
        if source_element.type in (NodeType.PARALLEL_GATEWAY, NodeType.EXCLUSIVE_GATEWAY, NodeType.EVENT_BASED_GATEWAY):
            return [edge.target for edge in source_element.outgoings]
        if source_element.type in NodeType:
            return [source_element.outgoing.target]
        return []

    def handle_parallel_gateway(start_element, outer_machine) -> Element:
        # 0. scan all path
        # 1. Create a new machine for every path
        # 2. Add all the elements between the start_element and end_element to the new machine
        # 3. If there is a gateway in the middle, call this function recursively
        # 4. Add the new machine to the outer machine
        # 5. Return the end_element of the new machine
        def find_merged_parallel_gateway(start_element) -> Element:
            # find the merged one for start_element parallel gateway
            # Attention  There may be Cycle
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
        
        print(f"START: handle elements between {start_element.id} and {end_element.id}")


        for idx, element in enumerate(next_elements(start_element)):
            # generate a new machine for every path
            new_machine = blank_machine.copy()
            new_machine["start_element"] = start_element
            new_machine["machine_name"] = f"{start_element.id} to {end_element.id} path {idx}"

            cursor = element
            print("FOR", element.id)
            print(end_element.id)
            while cursor.id != end_element.id:
                print(cursor.id)
                if not is_split_parallel_gateway(cursor):
                    new_machine["direct_elements"].append(cursor)
                    cursor = next_elements(cursor)[0]  # Emit Situation But Parallel Gateway
                    continue
                if is_split_parallel_gateway(cursor):
                    new_machine["direct_elements"].append(cursor)
                    end_element = handle_parallel_gateway(cursor, new_machine)
                    new_machine["direct_elements"].append(end_element)
                    cursor = end_element
                    continue

            outer_machine["nested_machines"][element] = new_machine
        
        print(f"END:handle elements between {start_element.id} and {end_element.id} ")

        return end_element

    def handle_exclusive_gateway(start_element, outer_machine) -> Element:
        # 1. Create a new machine
        # 2. Add all the elements between the start_element and end_element to the new machine
        # 3. If there is a gateway in the middle, call this function recursively
        # 4. Add the new machine to the outer machine
        # 5. Return the end_element of the new machine
        pass

    start_element = choreography.query_element_with_type(NodeType.START_EVENT)[0]
    end_element = choreography.query_element_with_type(NodeType.END_EVENT)[0]

    machine = {
        "start_element": start_element,  # commonly is startElement or a Gateway
        "machine_name": f"{start_element.id} to {end_element.id}",
        "direct_elements": [],
        "nested_machines": {},
    }

    blank_machine = {"start_element": None, "machine_name": "", "direct_elements": [], "nested_machines": {}}

    cursor = start_element
    while cursor.id != end_element.id:
        if cursor.type not in [NodeType.PARALLEL_GATEWAY]:
            machine["direct_elements"].append(cursor)
            assert len(next_elements(cursor)) == 1
            cursor = next_elements(cursor)[0]
            continue
        if cursor.type == NodeType.PARALLEL_GATEWAY:
            machine["direct_elements"].append(cursor)
            end_element = handle_parallel_gateway(cursor, machine)
            machine["direct_elements"].append(end_element)
            cursor = next_elements(end_element)[0]


if "__main__" == __name__:
    choreography = Choreography()
    choreography.load_diagram_from_xml_file("./bpmn_muti/parallel.bpmn")
    res = method_to_extract_parallel_gateway(choreography)