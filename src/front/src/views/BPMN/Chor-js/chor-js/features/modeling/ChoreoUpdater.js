import inherits from 'inherits';
import BpmnUpdater from 'bpmn-js/lib/features/modeling/BpmnUpdater';
import { is } from 'bpmn-js/lib/util/ModelUtil';
import { assign, pick } from 'min-dash';

/**
 * Override of BpmnUpdater because that one crashes with choreographies when updating
 * the shape as well as semantic parents.
 * @constructor
 * @param {Injector} injector
 */
export default function ChoreoUpdater(injector) {
  injector.invoke(BpmnUpdater, this);
  function updateBandBounds(bandShape) {
    assign(bandShape.diBand.bounds, pick(bandShape, ['x', 'y', 'width', 'height']));
  }
  this.executed(['shape.move', 'shape.resize'], event => {
    let shape = event.context.shape;
    if (is(shape, 'bpmn:Participant')) {
      updateBandBounds(shape);
    }
  });
  this.reverted(['shape.move', 'shape.resize'], event => {
    let shape = event.context.shape;
    if (is(shape, 'bpmn:Participant')) {
      updateBandBounds(shape);
    }
  });
}
inherits(ChoreoUpdater, BpmnUpdater);
ChoreoUpdater.$inject = ['injector'];
ChoreoUpdater.prototype.updateParent = function (element, oldParent) {
  if (!is(element, 'bpmn:Participant') && !is(element, 'bpmn:Message')) {
    BpmnUpdater.prototype.updateParent.call(this, element, oldParent);
  }
};
ChoreoUpdater.prototype.updateSemanticParent = function (businessObject, newParent, visualParent) {
  if (!is(businessObject, 'bpmn:Participant') && !is(businessObject, 'bpmn:Message')) {
    // Special handling for DataAssociation with ChoreographyActivity
    // DO NOT call BpmnUpdater for DataAssociation involving ChoreographyActivity
    // because ChoreographyActivity doesn't properly support DataAssociation in BPMN spec
    if (is(businessObject, 'bpmn:DataAssociation')) {
      console.log('[ChoreoUpdater.updateSemanticParent] DataAssociation detected:');
      console.log('  businessObject type:', businessObject.$type);
      console.log('  newParent:', newParent?.$type);
      console.log('  visualParent:', visualParent);
      console.log('  visualParent.source:', visualParent?.source?.businessObject.$type);
      console.log('  visualParent.target:', visualParent?.target?.businessObject.$type);

      // Check source and target from businessObject references
      const sourceRef = businessObject.sourceRef;
      const targetRef = businessObject.targetRef;

      console.log('  sourceRef:', sourceRef?.$type);
      console.log('  targetRef:', targetRef?.$type);

      // Check if either source or target is ChoreographyActivity
      const involvesChoreography =
        (sourceRef && is(sourceRef, 'bpmn:ChoreographyActivity')) ||
        (targetRef && is(targetRef, 'bpmn:ChoreographyActivity')) ||
        (visualParent?.source && is(visualParent.source, 'bpmn:ChoreographyActivity')) ||
        (visualParent?.target && is(visualParent.target, 'bpmn:ChoreographyActivity'));

      console.log('  involvesChoreography:', involvesChoreography);

      if (involvesChoreography) {
        console.log('[ChoreoUpdater.updateSemanticParent] Handling manually, NOT calling BpmnUpdater');

        // Handle DataAssociation manually for ChoreographyActivity
        // Add to parent container's flowElements if it exists
        if (newParent) {
          if (!newParent.flowElements) {
            newParent.flowElements = [];
          }
          if (!newParent.flowElements.includes(businessObject)) {
            newParent.flowElements.push(businessObject);
          }
        }

        // Add to source's dataOutputAssociations if applicable
        if (is(businessObject, 'bpmn:DataOutputAssociation') && sourceRef && is(sourceRef, 'bpmn:ChoreographyActivity')) {
          if (!sourceRef.dataOutputAssociations) {
            sourceRef.dataOutputAssociations = [];
          }
          if (!sourceRef.dataOutputAssociations.includes(businessObject)) {
            sourceRef.dataOutputAssociations.push(businessObject);
          }
        }

        // Add to target's dataInputAssociations if applicable
        if (is(businessObject, 'bpmn:DataInputAssociation') && targetRef && is(targetRef, 'bpmn:ChoreographyActivity')) {
          if (!targetRef.dataInputAssociations) {
            targetRef.dataInputAssociations = [];
          }
          if (!targetRef.dataInputAssociations.includes(businessObject)) {
            targetRef.dataInputAssociations.push(businessObject);
          }
        }

        // Set the parent reference
        businessObject.$parent = newParent;

        console.log('[ChoreoUpdater.updateSemanticParent] Manual handling complete, returning');
        // Don't call BpmnUpdater for ChoreographyActivity DataAssociation
        return;
      }

      console.log('[ChoreoUpdater.updateSemanticParent] NOT involving Choreography, will call BpmnUpdater');
    }

    // For all other cases, use default behavior
    BpmnUpdater.prototype.updateSemanticParent.call(this, businessObject, newParent, visualParent);
  }
};