#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from common import normalize_name


RELATIONS = {
    "==": lambda left, right: left == right,
    "!=": lambda left, right: left != right,
    ">=": lambda left, right: left is not None and left >= right,
    "<=": lambda left, right: left is not None and left <= right,
    ">": lambda left, right: left is not None and left > right,
    "<": lambda left, right: left is not None and left < right,
}


@dataclass
class ElementMeta:
    name: str
    kind: str
    initial_state: str
    extra: Dict[str, Any]


class DSLSimulator:
    def __init__(self, model: Dict[str, Any], case_name: str) -> None:
        self.model = model
        self.case_name = case_name
        self.elements: Dict[str, ElementMeta] = {}
        self.globals: Dict[str, Any] = {item["name"]: None for item in model.get("globals", [])}
        self.global_types: Dict[str, str] = {item["name"]: item["type"] for item in model.get("globals", [])}
        self.global_aliases: Dict[str, str] = {normalize_name(name): name for name in self.globals}
        self.parallel_joins = [flow for flow in model.get("flows", []) if flow.get("kind") == "parallel_join"]
        self.flows_by_trigger: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self.trace_steps: List[Dict[str, Any]] = []
        self.bootstrap_events: List[Dict[str, Any]] = []
        self.rejected = False
        self.rejection_reason = ""
        self._build_registry()
        self.states: Dict[str, str] = {name: meta.initial_state for name, meta in self.elements.items()}
        self._bootstrap()

    def _build_registry(self) -> None:
        for item in self.model.get("messages", []):
            self.elements[item["name"]] = ElementMeta(item["name"], "message", item.get("initial_state") or "INACTIVE", item)
        for item in self.model.get("gateways", []):
            self.elements[item["name"]] = ElementMeta(item["name"], "gateway", item.get("initial_state") or "INACTIVE", item)
        for item in self.model.get("events", []):
            self.elements[item["name"]] = ElementMeta(item["name"], "event", item.get("initial_state") or "INACTIVE", item)
        for item in self.model.get("businessrules", []):
            self.elements[item["name"]] = ElementMeta(item["name"], "businessrule", item.get("initial_state") or "INACTIVE", item)
        for item in self.model.get("oracletasks", []):
            self.elements[item["name"]] = ElementMeta(item["name"], "oracletask", item.get("initial_state") or "INACTIVE", item)

        for flow in self.model.get("flows", []):
            trigger = flow.get("trigger", {})
            key = (trigger.get("type"), trigger.get("name"))
            self.flows_by_trigger.setdefault(key, []).append(flow)

    def _bootstrap(self) -> None:
        for flow in self.model.get("flows", []):
            if flow.get("kind") != "start_flow":
                continue
            start_name = flow["trigger"]["name"]
            if self.states.get(start_name) != "READY":
                continue
            before = self.states.copy()
            self.states[start_name] = "DONE"
            branch_log = self._apply_actions(flow.get("actions", []))
            self.bootstrap_events.append(
                {
                    "trigger": {"type": "start", "name": start_name},
                    "state_diff": self._state_diff(before, self.states),
                    "applied_actions": branch_log,
                }
            )

    def enabled_elements(self) -> List[str]:
        return sorted(name for name, state in self.states.items() if state == "READY")

    def run_path(self, path_spec: Dict[str, Any]) -> Dict[str, Any]:
        for index, step in enumerate(path_spec.get("steps", [])):
            if self.rejected:
                break
            self._execute_step(index, step)

        final_status = "rejected" if self.rejected else "accepted"
        return {
            "case_name": self.case_name,
            "path_name": path_spec.get("path_name"),
            "platform": "dsl",
            "bootstrap": self.bootstrap_events,
            "steps": self.trace_steps,
            "final_state": {
                "status": final_status,
                "reason": self.rejection_reason if self.rejected else "",
                "enabled_elements": self.enabled_elements(),
                "element_states": deepcopy(self.states),
                "globals": deepcopy(self.globals),
            },
        }

    def _execute_step(self, index: int, step: Dict[str, Any]) -> None:
        element = step.get("element")
        trigger_type = step.get("type")
        enabled_before = self.enabled_elements()
        before_states = deepcopy(self.states)
        before_globals = deepcopy(self.globals)

        step_record: Dict[str, Any] = {
            "index": index,
            "trigger": {"type": trigger_type, "name": element},
            "enabled_before": enabled_before,
            "guard_result": True,
            "payload": step.get("payload", {}),
            "outputs": step.get("outputs", {}),
            "accepted": True,
            "logs": [],
        }

        if element not in self.elements:
            self._reject(step_record, f"unknown element: {element}")
            return
        if self.elements[element].kind != trigger_type:
            self._reject(step_record, f"element type mismatch: expected {self.elements[element].kind}, got {trigger_type}")
            return
        if self.states.get(element) != "READY":
            self._reject(step_record, f"element not triggerable: {element} is {self.states.get(element)}")
            return

        self.states[element] = "DONE"
        step_record["logs"].append(f"{trigger_type} {element} -> DONE")
        self._apply_input_updates(trigger_type, element, step, step_record["logs"])

        matched = self.flows_by_trigger.get((trigger_type, element), [])
        if trigger_type == "message":
            matched = [flow for flow in matched if flow.get("trigger", {}).get("state") in ("sent", "completed")]
        elif trigger_type == "businessrule":
            matched = [flow for flow in matched if flow.get("trigger", {}).get("state") == "done"]
        elif trigger_type == "oracletask":
            matched = [flow for flow in matched if flow.get("trigger", {}).get("state") == "done"]

        flow_logs: List[Dict[str, Any]] = []
        for flow in matched:
            flow_log = self._apply_flow(flow)
            flow_logs.append(flow_log)
            if flow_log.get("accepted") is False:
                step_record["flow_results"] = flow_logs
                step_record["state_diff"] = self._state_diff(before_states, self.states)
                step_record["global_diff"] = self._global_diff(before_globals, self.globals)
                self._reject(step_record, flow_log.get("reason", "flow evaluation failed"))
                return

        join_logs = self._apply_parallel_joins(step_record["logs"])
        step_record["flow_results"] = flow_logs + join_logs
        step_record["state_diff"] = self._state_diff(before_states, self.states)
        step_record["global_diff"] = self._global_diff(before_globals, self.globals)
        self.trace_steps.append(step_record)

    def _reject(self, step_record: Dict[str, Any], reason: str) -> None:
        step_record["guard_result"] = False
        step_record["accepted"] = False
        step_record["rejection_reason"] = reason
        self.rejected = True
        self.rejection_reason = reason
        self.trace_steps.append(step_record)

    def _apply_input_updates(self, trigger_type: str, element: str, step: Dict[str, Any], logs: List[str]) -> None:
        payload = step.get("payload", {}) or {}
        outputs = step.get("outputs", {}) or {}

        if trigger_type == "message":
            self._apply_global_alias_mapping(payload, logs, source="message payload")
            return

        if trigger_type == "businessrule":
            rule_meta = self.elements[element].extra
            self._apply_mapped_outputs(outputs, rule_meta.get("output_mapping", []), logs, source="businessrule output")
            return

        if trigger_type == "oracletask":
            task_meta = self.elements[element].extra
            self._apply_mapped_outputs(outputs, task_meta.get("output_mapping", []), logs, source="oracletask output")

    def _apply_mapped_outputs(self, outputs: Dict[str, Any], mappings: List[Dict[str, Any]], logs: List[str], *, source: str) -> None:
        mapping_by_param = {normalize_name(item.get("dmn_param")): item.get("global") for item in mappings}
        for key, value in outputs.items():
            global_name = mapping_by_param.get(normalize_name(key))
            if not global_name:
                global_name = self.global_aliases.get(normalize_name(key))
            if not global_name:
                continue
            coerced = self._coerce_value(global_name, value)
            self.globals[global_name] = coerced
            logs.append(f"{source}: set {global_name}={coerced!r}")

    def _apply_global_alias_mapping(self, payload: Dict[str, Any], logs: List[str], *, source: str) -> None:
        for key, value in payload.items():
            global_name = self.global_aliases.get(normalize_name(key))
            if not global_name:
                continue
            coerced = self._coerce_value(global_name, value)
            self.globals[global_name] = coerced
            logs.append(f"{source}: set {global_name}={coerced!r}")

    def _coerce_value(self, global_name: str, value: Any) -> Any:
        global_type = self.global_types.get(global_name)
        if global_type == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() == "true"
        if global_type == "int":
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.strip():
                return int(value)
        if global_type == "float":
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str) and value.strip():
                return float(value)
        return value

    def _apply_flow(self, flow: Dict[str, Any]) -> Dict[str, Any]:
        flow_log: Dict[str, Any] = {"kind": flow.get("kind"), "trigger": flow.get("trigger"), "accepted": True}
        if flow.get("kind") == "gateway_flow" and flow.get("conditions"):
            branch_log = self._apply_gateway_choice(flow.get("conditions", []))
            if branch_log["accepted"]:
                flow_log["selected_branch"] = branch_log
            else:
                flow_log["accepted"] = False
                flow_log["reason"] = branch_log["reason"]
            return flow_log

        flow_log["applied_actions"] = self._apply_actions(flow.get("actions", []))
        return flow_log

    def _apply_gateway_choice(self, branches: List[Dict[str, Any]]) -> Dict[str, Any]:
        selected: Dict[str, Any] | None = None
        for branch in branches:
            if self._branch_matches(branch):
                selected = branch
                break
        if not selected:
            return {"accepted": False, "reason": "no gateway branch matched"}

        return {
            "accepted": True,
            "condition_kind": selected.get("condition_kind"),
            "var": selected.get("var"),
            "relation": selected.get("relation"),
            "value": selected.get("value"),
            "expr": selected.get("expr"),
            "applied_actions": self._apply_actions(selected.get("actions", [])),
        }

    def _branch_matches(self, branch: Dict[str, Any]) -> bool:
        kind = branch.get("condition_kind")
        if kind == "else":
            return True
        if kind == "expression":
            return False
        if kind == "compare":
            left = self.globals.get(branch.get("var"))
            right = self._coerce_value(branch.get("var"), branch.get("value"))
            relation = RELATIONS.get(branch.get("relation"))
            return relation(left, right) if relation else False
        return False

    def _apply_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logs: List[Dict[str, Any]] = []
        for action in actions:
            kind = action.get("kind")
            target = action.get("target")
            if kind == "enable" and target in self.states:
                before = self.states[target]
                self.states[target] = "READY"
                logs.append({"kind": kind, "target": target, "from": before, "to": "READY"})
            elif kind == "disable" and target in self.states:
                before = self.states[target]
                self.states[target] = "INACTIVE"
                logs.append({"kind": kind, "target": target, "from": before, "to": "INACTIVE"})
            elif kind == "set" and target in self.globals:
                before = self.globals[target]
                after = self._coerce_value(target, action.get("value"))
                self.globals[target] = after
                logs.append({"kind": kind, "target": target, "from": before, "to": after})
        return logs

    def _apply_parallel_joins(self, logs: List[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for join in self.parallel_joins:
            gateway_name = join.get("trigger", {}).get("name")
            if not gateway_name:
                continue
            sources = join.get("conditions", [{}])[0].get("sources", [])
            gateway_state = self.states.get(gateway_name)
            done_sources = [name for name in sources if self.states.get(name) == "DONE"]
            if done_sources and gateway_state == "INACTIVE":
                self.states[gateway_name] = "PENDING_CONFIRMATION"
                logs.append(f"parallel gateway {gateway_name} -> PENDING_CONFIRMATION")
                gateway_state = "PENDING_CONFIRMATION"
            if gateway_state == "DONE":
                continue
            if sources and all(self.states.get(name) == "DONE" for name in sources):
                self.states[gateway_name] = "DONE"
                action_log = self._apply_actions(join.get("actions", []))
                results.append(
                    {
                        "kind": "parallel_join",
                        "gateway": gateway_name,
                        "sources": sources,
                        "accepted": True,
                        "applied_actions": action_log,
                    }
                )
        return results

    @staticmethod
    def _state_diff(before: Dict[str, str], after: Dict[str, str]) -> Dict[str, List[str]]:
        diff: Dict[str, List[str]] = {}
        for name, old_value in before.items():
            new_value = after.get(name)
            if old_value != new_value:
                diff[name] = [old_value, new_value]
        return diff

    @staticmethod
    def _global_diff(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, List[Any]]:
        diff: Dict[str, List[Any]] = {}
        for name, old_value in before.items():
            new_value = after.get(name)
            if old_value != new_value:
                diff[name] = [old_value, new_value]
        return diff
