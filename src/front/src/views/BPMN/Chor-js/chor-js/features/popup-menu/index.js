import PopupMenuModule from 'diagram-js/lib/features/popup-menu';
import ParticipantPopupProvider from './ParticipantPopupProvider';
import ReplaceMenuProvider from './ReplaceMenuProvider';
import LinkCallChoreoPopupProvider from './LinkCallChoreoPopupProvider';
import LoopPopupProvider from './LoopPopupProvider';
import ParticipantLinkingPopupProvider from './ParticipantLinkingPopupProvider';
import AssetTypePopupProvider from './AssetTypePopupProvider';
import AssetOperationPopupProvider from './AssetOperationPopupProvider';
export default {
  __depends__: [PopupMenuModule],
  __init__: ['participantPopupProvider', 'replaceMenuProvider', 'linkCallChoreoPopupProvider', 'loopPopupProvider', 'participantLinkingPopupProvider', 'assetTypePopupProvider', 'assetOperationPopupProvider'],
  participantPopupProvider: ['type', ParticipantPopupProvider],
  replaceMenuProvider: ['type', ReplaceMenuProvider],
  linkCallChoreoPopupProvider: ['type', LinkCallChoreoPopupProvider],
  loopPopupProvider: ['type', LoopPopupProvider],
  participantLinkingPopupProvider: ['type', ParticipantLinkingPopupProvider],
  assetTypePopupProvider: ['type', AssetTypePopupProvider],
  assetOperationPopupProvider: ['type', AssetOperationPopupProvider]
};
