import {stringProperty} from './PropertiesTool'

export default function participantDefinition(
	group,
	element,
	bpmnFactory,
	participantEventDefinition,
) {
    if (! element.businessObject.participantMultiplicity)
        return

	//   group.entries = group.entries.concat(createStructureRefTextField());

	group.entries = group.entries.concat(
		stringProperty(
			element,
			"participantMultiplicity",
			"maximum",
			"Maximum",
			true,
		),
	);
	group.entries = group.entries.concat(
		stringProperty(
			element,
			"participantMultiplicity",
			"minimum",
			"Minimum",
			true,
		),
	);
}

