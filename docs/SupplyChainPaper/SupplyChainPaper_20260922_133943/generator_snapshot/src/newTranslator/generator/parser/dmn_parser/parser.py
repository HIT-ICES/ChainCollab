import networkx as nx
import xml.etree.ElementTree as ET
import json
from collections import namedtuple


InformationRequirement = namedtuple("InformationRequirement", ["id", "type", "ref"])

DecisionInput = namedtuple(
    "DecisionInput", ["id", "label", "expression_id", "typeRef", "text"]
)
DecisionOutput = namedtuple("DecisionOutput", ["id", "name", "label", "type"])


class Element:
    def __init__(self, id, name):
        self._id = id
        self._name = name


class Decision(Element):
    _type = "decision"

    def __init__(
        self,
        decision_id,
        decision_name,
        information_requirements: list[InformationRequirement],
        inputs: list[DecisionInput] = [],
        outputs: list[DecisionOutput] = [],
    ):
        super().__init__(decision_id, decision_name)
        self.information_requirements: InformationRequirement = information_requirements
        self.inputs = inputs
        self.outputs = outputs

    def __str__(self):
        return f"""Decision: {self._name} ({self._id}) 
        
        Information Requirements: {self.information_requirements}

        Inputs: {self.inputs}

        Outputs: {self.outputs}
        """
    
    def __serialize__(self):
        return {
            "id": self._id,
            "name": self._name,
            "information_requirements": self.information_requirements,
            "inputs": self.inputs,
            "outputs": self.outputs
        }
    
    def deep_inputs(self, dmn):
        the_deep_inputs = []
        for input in self.inputs:
            # find information_requirements matched
            find_flag = False
            for requirement in self.information_requirements:
                if requirement.type == "requiredDecision" and requirement.ref == input.text:
                    decision = dmn.get_decision_by_id(requirement.ref)
                    the_deep_inputs.extend(decision.deep_inputs(dmn))
                    find_flag = True
                    break
            if not find_flag:
                the_deep_inputs.append(input)
        return the_deep_inputs


class InputData(Element):
    _type = "inputData"

    def __init__(self, data_id, data_name):
        super().__init__(data_id, data_name)


class DMNParser:
    # parse dependency relation only
    def __init__(self, dmn_content):
        self.dmn = dmn_content
        self.root = ET.fromstring(dmn_content)
        self.elements = []
        self.decisions = []
        self.input_data = []
        self._parse_elements(self.root)

    def _parse_elements(self, root):
        dmn_prefix = "{https://www.omg.org/spec/DMN/20191111/MODEL/}"
        for element in root:
            split_tag = element.tag.split("}")[1]
            requirements = []
            if split_tag == "decision":
                informationRequirementElements = element.findall(
                    f"{dmn_prefix}informationRequirement"
                )
                for informationRequirementElement in informationRequirementElements:
                    requiredInputElement = informationRequirementElement.findall(
                        f"{dmn_prefix}requiredInput"
                    )
                    if requiredInputElement:
                        requiredInput = requiredInputElement[0]
                        informationRequirement = InformationRequirement(
                            informationRequirementElement.attrib["id"],
                            "requiredInput",
                            requiredInput.attrib["href"].replace("#", ""),
                        )
                        requirements.append(informationRequirement)
                        continue
                    requiredDecisionElement = informationRequirementElement.findall(
                        f"{dmn_prefix}requiredDecision"
                    )
                    if requiredDecisionElement:
                        requiredDecision = requiredDecisionElement[0]
                        informationRequirement = InformationRequirement(
                            informationRequirementElement.attrib["id"],
                            "requiredDecision",
                            requiredDecision.attrib["href"].replace("#", ""),
                        )
                        requirements.append(informationRequirement)
                        continue

                decisionTable = element.find(f"{dmn_prefix}decisionTable")
                if decisionTable is None:
                    continue


                inputs = []
                inputElements = decisionTable.findall(f"{dmn_prefix}input")
                for inputElement in inputElements:
                    inputExpressionElement = inputElement.findall(
                        f"{dmn_prefix}inputExpression"
                    )[0]
                    input = DecisionInput(
                        inputElement.attrib["id"],
                        inputElement.attrib["label"],
                        inputExpressionElement.attrib["id"],
                        inputExpressionElement.attrib["typeRef"],
                        inputExpressionElement.find(f"{dmn_prefix}text").text,
                    )
                    inputs.append(input)

                outputs = []
                outputElements = decisionTable.findall(f"{dmn_prefix}output")
                for outputElement in outputElements:
                    output = DecisionOutput(
                        outputElement.attrib["id"],
                        outputElement.attrib["name"],
                        outputElement.attrib["label"],
                        outputElement.attrib["typeRef"],
                    )
                    outputs.append(output)

                decision = Decision(
                    element.attrib["id"],
                    element.attrib["name"],
                    requirements,
                    inputs,
                    outputs,
                )
                self.elements.append(decision)
            elif split_tag == "inputData":
                data = InputData(element.attrib["id"], element.attrib["name"])
                self.elements.append(data)
        return self.elements

    @classmethod
    def load_from_xml_string(cls, dmn_content: str):
        return cls(dmn_content)

    def get_all_elements_with_type(self, element_type):
        return [element for element in self.elements if element._type == element_type]

    def get_main_decision_id(self):
        decisions_be_depended = []
        all_decisions = self.get_all_elements_with_type("decision")
        for decision in all_decisions:
            for requirement in decision.information_requirements:
                if requirement.type == "requiredDecision":
                    decisions_be_depended.append(requirement.ref)
        main_decision = list(
            set([decision._id for decision in all_decisions])
            - set(decisions_be_depended)
        )
        if len(main_decision) > 1:
            raise ValueError("More than one main decision")
        elif len(main_decision) == 0:
            raise ValueError("No main decision")
        return main_decision[0]

    def get_decision_by_id(self, id):
        for element in self.elements:
            if element._id == id:
                return element
        return None
    
    def get_all_decisions(self):
        # mark the main one
        res = [
            decision for decision in self.elements if decision._type == "decision"
        ]
        for decision in res:
            if decision._id == self.get_main_decision_id():
                decision.is_main = True
            else:
                decision.is_main = False
        return res


if __name__ == "__main__":
    dmn_string = """<?xml version="1.0" encoding="UTF-8"?>
    <definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/" xmlns:dmndi="https://www.omg.org/spec/DMN/20191111/DMNDI/" xmlns:dc="http://www.omg.org/spec/DMN/20180521/DC/" xmlns:di="http://www.omg.org/spec/DMN/20180521/DI/" xmlns:camunda="http://camunda.org/schema/1.0/dmn" id="dish" name="Dish" namespace="test-drd-2">
    <decision id="dish-decision" name="Dish Decision">
        <informationRequirement id="InformationRequirement_0vlz5d3">
        <requiredDecision href="#season" />
        </informationRequirement>
        <informationRequirement id="InformationRequirement_0n92yrg">
        <requiredDecision href="#guestCount" />
        </informationRequirement>
        <informationRequirement id="InformationRequirement_0ylxtia">
        <requiredDecision href="#season" />
        </informationRequirement>
        <informationRequirement id="InformationRequirement_0tk9qtg">
        <requiredDecision href="#guestCount" />
        </informationRequirement>
        <decisionTable id="dishDecisionTable">
        <input id="seasonInput" label="Season">
            <inputExpression id="seasonInputExpression" typeRef="string">
            <text>season</text>
            </inputExpression>
        </input>
        <input id="guestCountInput" label="How many guests">
            <inputExpression id="guestCountInputExpression" typeRef="integer">
            <text>guestCount</text>
            </inputExpression>
        </input>
        <output id="output1" label="Dish" name="desiredDish" typeRef="string" />
        <rule id="row-495762709-1">
            <inputEntry id="UnaryTests_1nxcsjr">
            <text>"Winter"</text>
            </inputEntry>
            <inputEntry id="UnaryTests_1r9yorj">
            <text>&lt;=8</text>
            </inputEntry>
            <outputEntry id="LiteralExpression_1mtwzqz">
            <text>"Spareribs"</text>
            </outputEntry>
        </rule>
        <rule id="row-495762709-2">
            <inputEntry id="UnaryTests_1lxjbif">
            <text>"Winter"</text>
            </inputEntry>
            <inputEntry id="UnaryTests_0nhiedb">
            <text>&gt;8</text>
            </inputEntry>
            <outputEntry id="LiteralExpression_1h30r12">
            <text>"Pasta"</text>
            </outputEntry>
        </rule>
        <rule id="row-495762709-3">
            <inputEntry id="UnaryTests_0ifgmfm">
            <text>"Summer"</text>
            </inputEntry>
            <inputEntry id="UnaryTests_12cib9m">
            <text>&gt;10</text>
            </inputEntry>
            <outputEntry id="LiteralExpression_0wgaegy">
            <text>"Light salad"</text>
            </outputEntry>
        </rule>
        <rule id="row-495762709-7">
            <inputEntry id="UnaryTests_0ozm9s7">
            <text>"Summer"</text>
            </inputEntry>
            <inputEntry id="UnaryTests_0sesgov">
            <text>&lt;=10</text>
            </inputEntry>
            <outputEntry id="LiteralExpression_1dvc5x3">
            <text>"Beans salad"</text>
            </outputEntry>
        </rule>
        <rule id="row-445981423-3">
            <inputEntry id="UnaryTests_1er0je1">
            <text>"Spring"</text>
            </inputEntry>
            <inputEntry id="UnaryTests_1uzqner">
            <text>&lt;10</text>
            </inputEntry>
            <outputEntry id="LiteralExpression_1pxy4g1">
            <text>"Stew"</text>
            </outputEntry>
        </rule>
        <rule id="row-445981423-4">
            <inputEntry id="UnaryTests_06or48g">
            <text>"Spring"</text>
            </inputEntry>
            <inputEntry id="UnaryTests_0wa71sy">
            <text>&gt;=10</text>
            </inputEntry>
            <outputEntry id="LiteralExpression_09ggol9">
            <text>"Steak"</text>
            </outputEntry>
        </rule>
        </decisionTable>
    </decision>
    <decision id="season" name="Season decision">
        <informationRequirement id="InformationRequirement_0tys7ju">
        <requiredInput href="#InputData_12pld2m" />
        </informationRequirement>
        <decisionTable id="seasonDecisionTable">
        <input id="temperatureInput" label="Weather in Celsius">
            <inputExpression id="temperatureInputExpression" typeRef="integer">
            <text>temperature</text>
            </inputExpression>
        </input>
        <output id="seasonOutput" label="season" name="season" typeRef="string" />
        <rule id="row-495762709-5">
            <inputEntry id="UnaryTests_1fd0eqo">
            <text>&gt;30</text>
            </inputEntry>
            <outputEntry id="LiteralExpression_0l98klb">
            <text>"Summer"</text>
            </outputEntry>
        </rule>
        <rule id="row-495762709-6">
            <inputEntry id="UnaryTests_1nz6at2">
            <text>&lt;10</text>
            </inputEntry>
            <outputEntry id="LiteralExpression_08moy1k">
            <text>"Winter"</text>
            </outputEntry>
        </rule>
        <rule id="row-445981423-2">
            <inputEntry id="UnaryTests_1a0imxy">
            <text>[10..30]</text>
            </inputEntry>
            <outputEntry id="LiteralExpression_1poftw4">
            <text>"Spring"</text>
            </outputEntry>
        </rule>
        </decisionTable>
    </decision>
    <decision id="guestCount" name="Guest Count">
        <informationRequirement id="InformationRequirement_1tdycnb">
        <requiredInput href="#InputData_1ybv19l" />
        </informationRequirement>


        
        <decisionTable id="guestCountDecisionTable">
        <input id="typeOfDayInput" label="Type of day">
            <inputExpression id="typeOfDayInputExpression" typeRef="string">
            <text>dayType</text>
            </inputExpression>
        </input>
        <output id="guestCountOutput" label="Guest count" name="guestCount" typeRef="integer" />
        <rule id="row-495762709-8">
            <inputEntry id="UnaryTests_0l72u8n">
            <text>"WeekDay"</text>
            </inputEntry>
            <outputEntry id="LiteralExpression_0wuwqaz">
            <text>4</text>
            </outputEntry>
        </rule>
        <rule id="row-495762709-9">
            <inputEntry id="UnaryTests_03a73o9">
            <text>"Holiday"</text>
            </inputEntry>
            <outputEntry id="LiteralExpression_1whn119">
            <text>10</text>
            </outputEntry>
        </rule>
        <rule id="row-495762709-10">
            <inputEntry id="UnaryTests_12tygwt">
            <text>"Weekend"</text>
            </inputEntry>
            <outputEntry id="LiteralExpression_1b5k9t8">
            <text>15</text>
            </outputEntry>
        </rule>
        </decisionTable>
    </decision>


    
    <inputData id="InputData_12pld2m" name="temperature" />
    <inputData id="InputData_1ybv19l" name="dayType" />
    <dmndi:DMNDI>
        <dmndi:DMNDiagram id="DMNDiagram_0zqvrkc">
        <dmndi:DMNShape id="DMNShape_085mwzu" dmnElementRef="dish-decision">
            <dc:Bounds height="80" width="180" x="420" y="60" />
        </dmndi:DMNShape>
        <dmndi:DMNShape id="DMNShape_1fbh9l9" dmnElementRef="season">
            <dc:Bounds height="80" width="180" x="130" y="260" />
        </dmndi:DMNShape>
        <dmndi:DMNShape id="DMNShape_1lwjonf" dmnElementRef="guestCount">
            <dc:Bounds height="80" width="180" x="720" y="280" />
        </dmndi:DMNShape>
        <dmndi:DMNEdge id="DMNEdge_1t5agin" dmnElementRef="InformationRequirement_0ylxtia">
            <di:waypoint x="220" y="260" />
            <di:waypoint x="480" y="160" />
            <di:waypoint x="480" y="140" />
        </dmndi:DMNEdge>
        <dmndi:DMNEdge id="DMNEdge_0rs98c6" dmnElementRef="InformationRequirement_0tk9qtg">
            <di:waypoint x="810" y="280" />
            <di:waypoint x="540" y="160" />
            <di:waypoint x="540" y="140" />
        </dmndi:DMNEdge>
        <dmndi:DMNShape id="DMNShape_1l1qoeo" dmnElementRef="InputData_12pld2m">
            <dc:Bounds height="45" width="125" x="157" y="477" />
        </dmndi:DMNShape>
        <dmndi:DMNEdge id="DMNEdge_0tnxv4l" dmnElementRef="InformationRequirement_0tys7ju">
            <di:waypoint x="220" y="477" />
            <di:waypoint x="220" y="360" />
            <di:waypoint x="220" y="340" />
        </dmndi:DMNEdge>
        <dmndi:DMNShape id="DMNShape_14l4bbp" dmnElementRef="InputData_1ybv19l">
            <dc:Bounds height="45" width="125" x="757" y="517" />
        </dmndi:DMNShape>
        <dmndi:DMNEdge id="DMNEdge_1ar7p5v" dmnElementRef="InformationRequirement_1tdycnb">
            <di:waypoint x="820" y="517" />
            <di:waypoint x="810" y="380" />
            <di:waypoint x="810" y="360" />
        </dmndi:DMNEdge>
        </dmndi:DMNDiagram>
    </dmndi:DMNDI>
    </definitions>"""
    dmn = DMNParser.load_from_xml_string(dmn_string)
    
