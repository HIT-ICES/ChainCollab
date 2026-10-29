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
            root = ET.fromstring(dmn_content)
            namespace = root.tag.split('}')[0][1:]
            decisions_by_id, decisions_by_name = self._index_decisions(root, namespace)
            _, result_list = self._evaluate_decision(
                decision_id,
                decisions_by_id,
                decisions_by_name,
                namespace,
                dict(input_data or {}),
                {}
            )
            return result_list

        except Exception as e:
            raise Exception(f"DMN evaluation error: {str(e)}")

    def _index_decisions(self, root, namespace):
        decisions_by_id = {}
        decisions_by_name = {}
        for decision in root.findall(f".//{{{namespace}}}decision"):
            decision_id = decision.get('id')
            decision_name = decision.get('name')
            if decision_id:
                decisions_by_id[decision_id] = decision
            if decision_name:
                decisions_by_name[decision_name] = decision
        return decisions_by_id, decisions_by_name

    def _resolve_decision(self, decision_ref, decisions_by_id, decisions_by_name):
        decision = decisions_by_id.get(decision_ref)
        if decision is not None:
            return decision
        decision = decisions_by_name.get(decision_ref)
        if decision is not None:
            return decision
        raise ValueError(f"Decision '{decision_ref}' not found")

    def _get_decision_table(self, decision, namespace):
        decision_table = decision.find(f"./{{{namespace}}}decisionTable")
        if decision_table is None:
            decision_logic = decision.find(f"./{{{namespace}}}decisionLogic")
            if decision_logic is not None:
                decision_table = decision_logic.find(f"./{{{namespace}}}decisionTable")
        if decision_table is None:
            decision_id = decision.get('id') or decision.get('name') or '<unknown>'
            raise ValueError(f"Decision table for '{decision_id}' not found")
        return decision_table

    def _evaluate_decision(
        self,
        decision_ref,
        decisions_by_id,
        decisions_by_name,
        namespace,
        context,
        cache
    ):
        if decision_ref in cache:
            return cache[decision_ref]

        decision = self._resolve_decision(decision_ref, decisions_by_id, decisions_by_name)
        merged_context = dict(context)

        for info_req in decision.findall(f"./{{{namespace}}}informationRequirement"):
            required_decision = info_req.find(f"./{{{namespace}}}requiredDecision")
            if required_decision is None:
                continue
            href = required_decision.get('href')
            if not href:
                continue
            dependency_ref = href[1:] if href.startswith('#') else href
            dependency_decision, dependency_results = self._evaluate_decision(
                dependency_ref,
                decisions_by_id,
                decisions_by_name,
                namespace,
                merged_context,
                cache
            )
            if dependency_results:
                # Mirror Camunda-style evaluation semantics used in the old Fabric DMN contract:
                # later decisions can consume the first matched output row as input variables.
                merged_context.update(dependency_results[0])

        decision_table = self._get_decision_table(decision, namespace)
        results = self._evaluate_decision_table(decision_table, merged_context, namespace)

        cache_key = decision.get('id') or decision_ref
        resolved = (decision, results)
        cache[cache_key] = resolved
        decision_name = decision.get('name')
        if decision_name:
            cache[decision_name] = resolved
        return resolved

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
            return self._evaluate_range_expression(expression, value)
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

        if expression.lower() == 'true':
            return bool(value) is True
        if expression.lower() == 'false':
            return bool(value) is False

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

    def _evaluate_range_expression(self, expression, value):
        expr = expression.strip()
        if not expr:
            return False

        left_inclusive = True
        right_inclusive = True
        if expr[0] in '[(':
            left_inclusive = expr[0] == '['
            expr = expr[1:]
        if expr and expr[-1] in '])':
            right_inclusive = expr[-1] == ']'
            expr = expr[:-1]

        try:
            min_raw, max_raw = [part.strip() for part in expr.split('..', 1)]
            min_val = float(min_raw)
            max_val = float(max_raw)
        except Exception:
            return False

        left_ok = value >= min_val if left_inclusive else value > min_val
        right_ok = value <= max_val if right_inclusive else value < max_val
        return left_ok and right_ok

    def _parse_value(self, value_str, type_ref):
        """
        Parse output value based on type reference.
        """
        if value_str is None or value_str.strip() == "":
            return None

        value_str = value_str.strip()

        # Remove quotes if present
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            value_str = value_str[1:-1]

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
