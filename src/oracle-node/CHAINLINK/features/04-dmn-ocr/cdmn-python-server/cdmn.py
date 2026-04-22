import xml.etree.ElementTree as ET
import json
import re


class DMNEngine:
    """
    CDMN (Compact DMN) Engine wrapper for DMN 1.3 decision evaluation.
    """

    def __init__(self):
        self.ns = {
            'dmn': 'http://www.omg.org/spec/DMN/20191111/MODEL/',
            'dmn11': 'http://www.omg.org/spec/DMN/20151101/dmn.xsd',
            'dc': 'http://www.omg.org/spec/DMN/20191111/DC/',
            'di': 'http://www.omg.org/spec/DMN/20191111/DI/',
            'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI'
        }

    def evaluate(self, dmn_content, decision_id, input_data):
        """
        Evaluate a DMN decision.
        """
        try:
            # Parse DMN XML
            root = ET.fromstring(dmn_content)

            # Determine the DMN version and namespace
            # Check for DMN 1.3 (2019) or DMN 1.1 (2015)
            namespace = root.tag.split('}')[0][1:]
            if namespace == 'http://www.omg.org/spec/DMN/20151101/dmn.xsd':
                dmn_ns = 'dmn11'
            else:
                dmn_ns = 'dmn'

            # Find decision with specified id
            decision = root.find(f".//{{{namespace}}}decision[@id='{decision_id}']")
            if decision is None:
                raise ValueError(f"Decision '{decision_id}' not found")

            # Get decision logic (DMN 1.1 has decisionTable directly under decision)
            decision_table = decision.find(f".//{{{namespace}}}decisionTable")
            if decision_table is None:
                # Check for DMN 1.3 decisionLogic wrapper
                decision_logic = decision.find(f".//{{{namespace}}}decisionLogic")
                if decision_logic is not None:
                    decision_table = decision_logic.find(f".//{{{namespace}}}decisionTable")

            if decision_table is None:
                raise ValueError(f"Decision table for '{decision_id}' not found")

            # Evaluate decision table
            return self._evaluate_decision_table(decision_table, input_data, namespace)

        except Exception as e:
            raise Exception(f"DMN evaluation error: {str(e)}")

    def _evaluate_decision_table(self, decision_table, input_data, namespace):
        """
        Evaluate a decision table.
        """
        # Get input clauses
        input_clauses = decision_table.findall(f".//{{{namespace}}}input")
        inputs = []
        for clause in input_clauses:
            input_ref = clause.find(f".//{{{namespace}}}inputExpression/{{{namespace}}}text")
            if input_ref is not None and input_ref.text:
                inputs.append(input_ref.text.strip())

        # Get output clauses
        output_clauses = decision_table.findall(f".//{{{namespace}}}output")
        outputs = []
        for clause in output_clauses:
            outputs.append({
                'id': clause.get('id', ''),
                'name': clause.get('name', ''),
                'label': clause.get('label', ''),
                'typeRef': clause.get('typeRef', 'string')
            })

        # Get rules
        rules = decision_table.findall(f".//{{{namespace}}}rule")
        matching_results = []

        for rule in rules:
            # Evaluate input entries
            matches = True
            input_entries = rule.findall(f".//{{{namespace}}}inputEntry")

            for i, entry in enumerate(input_entries):
                entry_text_elem = entry.find(f".//{{{namespace}}}text")
                if entry_text_elem is None or not entry_text_elem.text:
                    continue
                entry_text = entry_text_elem.text.strip()
                if i < len(inputs) and not self._evaluate_expression(entry_text, inputs[i], input_data):
                    matches = False
                    break

            if matches:
                # Collect output entries if rule matches
                result = {}
                output_entries = rule.findall(f".//{{{namespace}}}outputEntry")

                for j, entry in enumerate(output_entries):
                    entry_text_elem = entry.find(f".//{{{namespace}}}text")
                    if entry_text_elem is None or not entry_text_elem.text:
                        continue
                    entry_text = entry_text_elem.text.strip()
                    if j < len(outputs):
                        output_info = outputs[j]
                        value = self._parse_value(entry_text, output_info.get('typeRef'))
                        result_key = output_info.get('name') or output_info.get('id') or output_info.get('label') or f'output_{j}'
                        result[result_key] = value

                if result:
                    matching_results.append(result)

        return matching_results

    def _evaluate_expression(self, expression, variable, input_data):
        """
        Evaluate an input expression.
        """
        if variable not in input_data:
            return False

        value = input_data[variable]
        expression = expression.strip()

        # Handle comparison operators
        if expression.startswith('>='):
            return value >= float(expression[2:])
        if expression.startswith('<='):
            return value <= float(expression[2:])
        if expression.startswith('>'):
            return value > float(expression[1:])
        if expression.startswith('<'):
            return value < float(expression[1:])
        if '..' in expression:
            # Range comparison (inclusive), handling [x..y] or x..y format
            range_str = expression.strip('[]')
            min_val, max_val = map(float, range_str.split('..'))
            return min_val <= value <= max_val
        if expression.startswith('not(') and expression.endswith(')'):
            # Not operator
            sub_expr = expression[4:-1].strip()
            return not self._evaluate_expression(sub_expr, variable, input_data)
        if 'or' in expression:
            # Or operator
            parts = expression.split('or')
            return any(self._evaluate_expression(part.strip(), variable, input_data) for part in parts)
        if 'and' in expression:
            # And operator
            parts = expression.split('and')
            return all(self._evaluate_expression(part.strip(), variable, input_data) for part in parts)

        # Exact match
        try:
            # Try to parse as number
            expr_val = float(expression)
            return value == expr_val
        except ValueError:
            # String match
            # Remove quotes if present
            if (expression.startswith('"') and expression.endswith('"')) or \
               (expression.startswith("'") and expression.endswith("'")):
                expression = expression[1:-1]
            return str(value) == str(expression)

    def _parse_value(self, value_str, type_ref):
        """
        Parse output value based on type reference.
        """
        if value_str is None or value_str.strip() == "":
            return None

        value_str = value_str.strip()

        value_str = self._normalize_string_literal(value_str)

        # Try to parse based on type
        if type_ref.lower() in ['number', 'integer', 'double', 'long']:
            try:
                if '.' in value_str:
                    return float(value_str)
                return int(value_str)
            except ValueError:
                pass
        elif type_ref.lower() in ['boolean']:
            lower_val = value_str.lower()
            if lower_val in ['true', 'yes', '1']:
                return True
            if lower_val in ['false', 'no', '0']:
                return False
        elif type_ref.lower() in ['string']:
            return value_str

        # Fallback to string
        return value_str

    def _normalize_string_literal(self, value):
        """
        Normalize DMN string literals to plain string values.

        Examples:
        - '"VeryLow"' -> 'VeryLow'
        - '\\"VeryLow\\"' -> 'VeryLow'
        - "'VeryLow'" -> 'VeryLow'
        """
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return text

        previous = None
        while text and text != previous:
            previous = text
            try:
                parsed = json.loads(text)
                if isinstance(parsed, str):
                    text = parsed.strip()
                    continue
            except Exception:
                pass

            if (text.startswith('"') and text.endswith('"')) or \
               (text.startswith("'") and text.endswith("'")):
                text = text[1:-1].strip()

        return text

    def get_input_info(self, dmn_content):
        """
        Get input information from DMN model.
        """
        try:
            root = ET.fromstring(dmn_content)

            # Determine the DMN version and namespace
            namespace = root.tag.split('}')[0][1:]

            # Find all decisions
            decisions = root.findall(f".//{{{namespace}}}decision")
            input_info = []
            process_input_list = []

            for decision in decisions:
                decision_id = decision.get('id')

                # Parse information requirements (to exclude process inputs)
                information_requirements = decision.findall(f".//{{{namespace}}}informationRequirement")
                for info_req in information_requirements:
                    required_decision = info_req.find(f".//{{{namespace}}}requiredDecision")
                    if required_decision is not None and 'href' in required_decision.attrib:
                        href = required_decision.attrib['href']
                        if href.startswith('#'):
                            process_input_list.append(href[1:])

                # Find decision logic (DMN 1.1 has decisionTable directly under decision)
                decision_table = decision.find(f".//{{{namespace}}}decisionTable")
                if decision_table is None:
                    # Check for DMN 1.3 decisionLogic wrapper
                    decision_logic = decision.find(f".//{{{namespace}}}decisionLogic")
                    if decision_logic is not None:
                        decision_table = decision_logic.find(f".//{{{namespace}}}decisionTable")

                if decision_table is not None:
                    # Get input clauses
                    input_clauses = decision_table.findall(f".//{{{namespace}}}input")

                    for clause in input_clauses:
                        input_id = clause.get('id', '')
                        input_label = clause.get('label', '')

                        input_expression = clause.find(f".//{{{namespace}}}inputExpression")
                        if input_expression is not None:
                            expression = input_expression.find(f".//{{{namespace}}}text")
                            expression_text = expression.text.strip() if expression is not None and expression.text else ''
                            type_ref = input_expression.get('typeRef', 'string')

                            input_info.append({
                                'key': input_id,
                                'label': input_label,
                                'type': type_ref,
                                'name': expression_text
                            })

            # Remove process inputs from data info list
            filtered_input_info = []
            for info in input_info:
                if info['key'] not in process_input_list:
                    filtered_input_info.append(info)

            return filtered_input_info

        except Exception as e:
            raise Exception(f"Error parsing DMN input info: {str(e)}")
