import entryFactory from "bpmn-js-properties-panel/lib/factory/EntryFactory";
import cmdHelper from "bpmn-js-properties-panel/lib/helper/CmdHelper";


export function stringProperty(element, position, property, label, validate) {
	// position is root or its children, means write the property to the loot tag or a children tag of root

	function readValue() {
		if (position === "root") {
			return element.businessObject.get(property);
		}
		return element.businessObject.get(position)[property];
	}

	function writeValue(value) {
		if (position === "root") {
			return cmdHelper.updateBusinessObject(element, element.businessObject, {
				[property]: value,
			});
		}
		// read the old one, and change it, then write it to
		var targetProperty = element.businessObject.get(position);
		targetProperty[property] = value;
		return cmdHelper.updateBusinessObject(element, element.businessObject, {
			[position]: targetProperty,
		});
	}

	return entryFactory.textField({
		id: property,
		label: label,
		modelProperty: property,

		get: function (element) {
			var values = {};
			values[property] = readValue();

			return values;
		},

		set: function (element, values) {
			// console.log(values) {maximum: '5'}
			return writeValue(values[property]);
		},

		validate: validate,
	});
}

export function booleanProperty(element, position, property, label) {
    function readValue() {
        if (position === "root") {
            return element.businessObject.get(property);
        }
        return element.businessObject.get(position)[property];
    }

    function writeValue(value) {
        if (position === "root") {
            return cmdHelper.updateBusinessObject(element, element.businessObject, {
                [property]: value,
            });
        }
        // read the old one, and change it, then write it to
        var targetProperty = element.businessObject.get(position);
        targetProperty[property] = value;
        return cmdHelper.updateBusinessObject(element, element.businessObject, {
            [position]: targetProperty,
        });
    }

    return entryFactory.checkbox({
        id: property,
        label: label,
        modelProperty: property,

        get: function (element) {
            var values = {};
            values[property] = readValue();

            return values;
        },

        set: function (element, values) {
            return writeValue(values[property]);
        },
    });
}
