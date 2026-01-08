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
      // CRITICAL: Also check newParent because sourceRef/targetRef may not be set yet when this is called
      const involvesChoreography =
        (sourceRef && is(sourceRef, 'bpmn:ChoreographyActivity')) ||
        (targetRef && is(targetRef, 'bpmn:ChoreographyActivity')) ||
        (visualParent?.source && is(visualParent.source, 'bpmn:ChoreographyActivity')) ||
        (visualParent?.target && is(visualParent.target, 'bpmn:ChoreographyActivity')) ||
        is(newParent, 'bpmn:ChoreographyActivity');

      console.log('  involvesChoreography:', involvesChoreography);

      if (involvesChoreography) {
        console.log('[ChoreoUpdater.updateSemanticParent] Handling manually, NOT calling BpmnUpdater');

        let activityBo = null;
        if (sourceRef && is(sourceRef, 'bpmn:ChoreographyActivity')) {
          activityBo = sourceRef;
        } else if (targetRef && is(targetRef, 'bpmn:ChoreographyActivity')) {
          activityBo = targetRef;
        } else if (visualParent?.source && is(visualParent.source, 'bpmn:ChoreographyActivity')) {
          activityBo = visualParent.source.businessObject;
        } else if (visualParent?.target && is(visualParent.target, 'bpmn:ChoreographyActivity')) {
          activityBo = visualParent.target.businessObject;
        } else if (is(newParent, 'bpmn:ChoreographyActivity')) {
          activityBo = newParent;
        }

        if (activityBo) {
          businessObject.$parent = activityBo;
          if (is(businessObject, 'bpmn:DataInputAssociation')) {
            if (!activityBo.dataInputAssociations) {
              activityBo.dataInputAssociations = [];
            }
            if (!activityBo.dataInputAssociations.includes(businessObject)) {
              activityBo.dataInputAssociations.push(businessObject);
            }
          } else if (is(businessObject, 'bpmn:DataOutputAssociation')) {
            if (!activityBo.dataOutputAssociations) {
              activityBo.dataOutputAssociations = [];
            }
            if (!activityBo.dataOutputAssociations.includes(businessObject)) {
              activityBo.dataOutputAssociations.push(businessObject);
            }
          }

          if (activityBo.$parent && activityBo.$parent.flowElements) {
            const idx = activityBo.$parent.flowElements.indexOf(businessObject);
            if (idx !== -1) {
              activityBo.$parent.flowElements.splice(idx, 1);
            }
          }
        } else {
          businessObject.$parent = newParent;
        }

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