import networkx as nx
import xml.etree.ElementTree as ET


class Decision:
    def __init__(self, decision_id, decision_name, decision_logic):
        self.id = decision_id
        self.name = decision_name
        self.logic = decision_logic

class InputData:
    def __init__(self, data_id, data_name, data_type):
        self.id = data_id
        self.name = data_name
        self.type = data_type


class DMN:
    def __init__(self, dmn_content):
        self.dmn = dmn_content

    def load_from_xml_string(dmn_content:str):
        return DMN(dmn_content)
    
    def get_main_decision_id(self):
        root = ET.fromstring(self.dmn)
        # find the main decisionID

