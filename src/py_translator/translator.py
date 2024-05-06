from typing import List, Optional, Tuple, Any, Protocol
from choreography_parser.elements import ElementProtocol, GraphProtocol
from choreography_parser.parser import Choreography

class GoChaincodeTranslator:
    def __init__ (self):
        pass


    def _generate_dependencies(self):
        pass



    def generate_chaincode(self, bpmn_file_path: str, output_path: str = "./chaincode.go"):
        choreography: Choreography = Choreography(bpmn_file_path)

        # how to generate

    