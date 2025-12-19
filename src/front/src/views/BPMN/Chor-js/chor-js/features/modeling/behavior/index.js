import CreateChoreoTaskBehavior from './CreateChoreoTaskBehavior';
import RemoveParticipantBehavior from './RemoveParticipantBehavior';
import ResizeParticipantBandBehavior from './ResizeParticipantBandBehavior';
import DeleteMessageBehavior from './DeleteMessageBehavior';
import ToggleChoreoCollapseBehaviour from './ToggleChoreoCollapseBehavior';
import ChoreoSpaceToolBehavior from './ChoreoSpaceToolBehavior';
import DataAssociationBehavior from './DataAssociationBehavior';
export default {
  __init__: ['createChoreoTaskBehavior', 'removeParticipantBehavior', 'resizeParticipantBehavior', 'deleteMessageBehavior', 'toggleChoreoCollapseBehavior', 'choreoSpaceToolBehavior', 'dataAssociationBehavior'],
  createChoreoTaskBehavior: ['type', CreateChoreoTaskBehavior],
  removeParticipantBehavior: ['type', RemoveParticipantBehavior],
  resizeParticipantBehavior: ['type', ResizeParticipantBandBehavior],
  deleteMessageBehavior: ['type', DeleteMessageBehavior],
  toggleChoreoCollapseBehavior: ['type', ToggleChoreoCollapseBehaviour],
  choreoSpaceToolBehavior: ['type', ChoreoSpaceToolBehavior],
  dataAssociationBehavior: ['type', DataAssociationBehavior]
};