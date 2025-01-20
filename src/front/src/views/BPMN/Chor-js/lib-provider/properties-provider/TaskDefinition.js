import eventDefinitionReference from "bpmn-js-properties-panel/lib/provider/bpmn/parts/implementation/EventDefinitionReference";
import elementReferenceProperty from "bpmn-js-properties-panel/lib/provider/bpmn/parts/implementation/ElementReferenceProperty";
import {stringProperty} from './PropertiesTool'

export default function choreographyTaskDefinition(
    group,
    element,
    bpmnFactory,
    taskDefinitionEventDefinition,
) {
    if (! element.businessObject.loopType)
        return

    if (element.businessObject.loopType === "Standard") {
        group.entries = group.entries.concat(
            stringProperty(
                element,
                "root",
                "loopCardinality",
                "Loop Cardinality",
                true,
            ),
        );
        group.entries = group.entries.concat(
            stringProperty(
                element,
                "root",
                "completionCondition",
                "Completion Condition",
                true,
            ),
        );
    }

    if (element.businessObject.loopType === 'MultiInstanceParallel'){
        group.entries = group.entries.concat(
            stringProperty(
                element,
                "root",
                "loopCardinality",
                "Loop Cardinality",
                true,
            ),
        );
    }

    if (element.businessObject.loopType === 'MultiInstanceSequential'){
        group.entries = group.entries.concat(
            stringProperty(
                element,
                "root",
                "loopCardinality",
                "Loop Cardinality",
                true,
            ));
    }
}

