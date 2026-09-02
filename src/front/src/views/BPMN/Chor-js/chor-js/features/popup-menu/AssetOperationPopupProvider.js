import inherits from 'inherits';
import PopupMenuProvider from 'diagram-js/lib/features/popup-menu/PopupMenuProvider';
import {
  applyAssetOperation,
  getAssetData,
  getAssetOperationData,
  getAssetOperationOptions,
  getPrimaryAssetElement
} from '../../../utils/assetExtension';

const OPERATION_ICON_CLASS = {
  mint: 'asset-operation-mint',
  burn: 'asset-operation-burn',
  'grant usage rights': 'asset-operation-grant',
  'revoke usage rights': 'asset-operation-revoke',
  transfer: 'asset-operation-transfer',
  Transfer: 'asset-operation-transfer',
  query: 'asset-operation-query',
  branch: 'asset-operation-branch',
  merge: 'asset-operation-merge'
};

export default function AssetOperationPopupProvider(injector, popupMenu, modeling, moddle, elementRegistry) {
  injector.invoke(PopupMenuProvider, this);
  this._popupMenu = popupMenu;
  this._modeling = modeling;
  this._moddle = moddle;
  this._elementRegistry = elementRegistry;
}

inherits(AssetOperationPopupProvider, PopupMenuProvider);

AssetOperationPopupProvider.$inject = ['injector', 'popupMenu', 'modeling', 'moddle', 'elementRegistry'];

AssetOperationPopupProvider.prototype.getHeaderEntries = function(element) {
  const primaryAssetElement = getPrimaryAssetElement(element, this._elementRegistry);
  const assetData = primaryAssetElement ? getAssetData(primaryAssetElement) : null;
  const currentOperation = getAssetOperationData(element).operation;

  return getAssetOperationOptions(assetData).map(operation => ({
    id: 'asset-operation-' + operation.replace(/\s+/g, '-').toLowerCase(),
    className: 'asset-operation-icon ' + OPERATION_ICON_CLASS[operation],
    title: operation,
    active: currentOperation === operation,
    action: () => applyAssetOperation(element, this._moddle, this._modeling, operation, assetData)
  }));
};

AssetOperationPopupProvider.prototype.getEntries = function() {
  return [];
};

AssetOperationPopupProvider.prototype.register = function() {
  this._popupMenu.registerProvider('asset-operation-provider', this);
};
