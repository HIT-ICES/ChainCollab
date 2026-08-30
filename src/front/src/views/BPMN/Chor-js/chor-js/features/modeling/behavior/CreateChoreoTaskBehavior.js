import inherits from 'inherits';
import CommandInterceptor from 'diagram-js/lib/command/CommandInterceptor';
import { is } from 'bpmn-js/lib/util/ModelUtil';
import { flatten } from 'min-dash';
import { getConnectedElements, isChoreoActivity, isInitiating } from '../../../util/DiagramWalkerUtil';
import { CONTRACT_PARTICIPANT_ID, CONTRACT_PARTICIPANT_NAME, getAssetOperation, isContractParticipant } from '../../../../utils/assetExtension';

/**
 *
 * @param hints
 * @param choreo
 * @returns {*}
 */
function chooseParticipants(hints, choreo) {
  // In the default case no source shape was given, e.g. because the the activity was dragged from the side pallet.
  const allParticipants = getBusinessParticipants(choreo);
  if (allParticipants.length < 2) {
    return {};
  }
  const recommended = {
    initiator: allParticipants[0],
    receiver: allParticipants[1]
  };
  if (hints && hints.sourceShape) {
    let source = hints.sourceShape;
    const precedingActivities = getConnectedElements(hints.sourceShape, 'incoming', isChoreoActivity);
    if (isChoreoActivity(source) || precedingActivities.length === 1) {
      // We reverse the participants roles compared to the previous activity.
      const participants = (isChoreoActivity(source) ? source.bandShapes : precedingActivities[0].bandShapes)
        .filter(p => !isContractParticipant(p.businessObject));
      const initiating = participants.find(p => isInitiating(p));
      const nonInitiating = participants.find(p => !isInitiating(p));
      recommended.receiver = initiating ? initiating.businessObject : recommended.receiver;
      recommended.initiator = nonInitiating ? nonInitiating.businessObject : recommended.initiator;
    } else if (precedingActivities.length > 1) {
      // If there are more than two preceding activities, e.g., due to a join we select the most used participants.
      const participants = flatten(precedingActivities.map(p => p.bandShapes.map(bs => bs.businessObject)))
        .filter(participant => !isContractParticipant(participant));
      const count = {};
      participants.forEach(bo => {
        count[bo.id] = (count[bo.id] || 0) + 1;
      });
      let list = allParticipants.map(bo => [bo, count[bo.id]]);
      list.sort((a, b) => b[1] - a[1]);
      recommended.initiator = list[0][0];
      recommended.receiver = list[1][0];
    }
  }
  return recommended;
}

function getBusinessParticipants(choreo) {
  return (choreo.businessObject.get('participants') || [])
    .filter(participant => !isContractParticipant(participant));
}

function getOrCreateContractParticipant(choreo, bpmnFactory) {
  let participants = choreo.businessObject.get('participants') || [];
  let contractParticipant = participants.find(participant =>
    participant.id === CONTRACT_PARTICIPANT_ID
  );

  if (!contractParticipant) {
    contractParticipant = bpmnFactory.create('bpmn:Participant', {
      id: CONTRACT_PARTICIPANT_ID,
      name: CONTRACT_PARTICIPANT_NAME
    });
    contractParticipant.$parent = choreo.businessObject;
    participants.push(contractParticipant);
    choreo.businessObject.participants = participants;
  }

  return contractParticipant;
}

/**
 * Behavior when creating a choreography task.
 * @constructor
 * @param {Injector} injector
 * @param {BpmnFactory} bpmnFactory
 * @param {Canvas} canvas
 * @param {ElementFactory} elementFactory
 * @param {BPMNModdle} model
 * @param {CommandStack} commandStack
 */
export default function CreateChoreoTaskBehavior(injector, bpmnFactory, canvas, elementFactory, model, commandStack) {
  injector.invoke(CommandInterceptor, this);
  this.preExecuted('shape.create', function (event) {
    const context = event.context;
    const shape = context.shape;
    if (is(shape, 'bpmn:ChoreographyActivity') && shape.type !== 'label') {
      console.log('[CreateChoreoTaskBehavior] preExecuted shape.create:');
      console.log('  Shape type:', shape.type);
      console.log('  BusinessObject type:', shape.businessObject.$type);
      console.log('  Has name:', shape.businessObject.name);

      if (!shape.businessObject.name) {
        shape.businessObject.name = 'New Activity';
      }
    }
  });
  this.postExecuted('shape.create', function (event) {
    let context = event.context;
    let shape = context.shape;
    const businessObject = shape.businessObject;
    if (is(shape, 'bpmn:ChoreographyActivity') && shape.type !== 'label') {
      console.log('[CreateChoreoTaskBehavior] postExecuted shape.create START:');
      console.log('  Shape type:', shape.type);
      console.log('  BusinessObject type:', businessObject.$type);
      console.log('  bandShapes exists:', !!shape.bandShapes);
      console.log('  participantRef length:', businessObject.participantRef?.length);

      let participants = [];
      if (context.hints.createElementsBehavior === false) {
        // the shape was copied
        participants = [].concat(businessObject.participantRef);
        businessObject.participantRef = []; // will be set by CreateParticipantBandHandler
      } else {
        const choreo = canvas.getRootElement();
        const recommended = chooseParticipants(context.hints, choreo);
        const isAssetTask = getAssetOperation(shape);
        const initiator = recommended.initiator || getBusinessParticipants(choreo)[0];
        participants[0] = initiator;
        participants[1] = isAssetTask
          ? getOrCreateContractParticipant(choreo, bpmnFactory)
          : recommended.receiver;
        businessObject.initiatingParticipantRef = initiator;
        if (!businessObject.participantRef) {
          businessObject.participantRef = [];
        }
      }
      if (!shape.bandShapes) {
        shape.bandShapes = [];
      }
      participants.forEach((p, i) => {
        const bandContext = {
          delete: false,
          activityShape: shape,
          index: i,
          isInitiating: businessObject.initiatingParticipantRef === p,
          participant: p
        };
        // if the participant has not been created yet, the CreateParticipantBandHandler will create a new one
        commandStack.execute('band.create', bandContext);
      });

      // create initiating message flow and shape (invisible)
      if (is(shape, 'bpmn:ChoreographyTask')) {
        if (businessObject.messageHints) {
          const hints = businessObject.messageHints;
          hints.forEach(mh => {
            const messageContext = {
              bandShape: shape.bandShapes.find(s => s.businessObject === mh.sourceRef),
              isVisible: mh.isVisible,
              name: mh.name
            };
            commandStack.execute('message.add', messageContext);
          });
          delete businessObject.messageHints;
        } else {
          const messageContext = {
            bandShape: shape.bandShapes.find(s => s.businessObject === businessObject.initiatingParticipantRef),
            isVisible: false
          };
          commandStack.execute('message.add', messageContext);
        }
      }

      console.log('[CreateChoreoTaskBehavior] postExecuted shape.create END:');
      console.log('  Shape type:', shape.type);
      console.log('  BusinessObject type:', businessObject.$type);
      console.log('  bandShapes length:', shape.bandShapes?.length);
      console.log('  participantRef length:', businessObject.participantRef?.length);
    }
  });
}
CreateChoreoTaskBehavior.$inject = ['injector', 'bpmnFactory', 'canvas', 'elementFactory', 'moddle', 'commandStack'];
inherits(CreateChoreoTaskBehavior, CommandInterceptor);
