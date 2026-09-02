import inherits from 'inherits';
import PopupMenuProvider from 'diagram-js/lib/features/popup-menu/PopupMenuProvider';
import {
  applyAssetCategory,
  applyTransferableTokenType,
  ASSET_CATEGORY_OPTIONS,
  TRANSFERABLE_TOKEN_TYPE_OPTIONS,
  getAssetData,
  isAssetElement
} from '../../../utils/assetExtension';

export default function AssetTypePopupProvider(injector, popupMenu, modeling) {
  injector.invoke(PopupMenuProvider, this);
  this._popupMenu = popupMenu;
  this._modeling = modeling;
}

inherits(AssetTypePopupProvider, PopupMenuProvider);

AssetTypePopupProvider.$inject = ['injector', 'popupMenu', 'modeling'];

AssetTypePopupProvider.prototype.getHeaderEntries = function(element) {
  if (!isAssetElement(element)) {
    return [];
  }

  const currentData = getAssetData(element);

  const categoryEntries = ASSET_CATEGORY_OPTIONS.map(option => ({
    id: 'asset-category-' + option.key,
    className: 'asset-kind-icon asset-category-icon asset-category-' + option.key,
    title: option.label,
    active: currentData.assetType === option.assetType,
    action: () => applyAssetCategory(element, this._modeling, option.assetType)
  }));

  return [
    ...categoryEntries,
    ...TRANSFERABLE_TOKEN_TYPE_OPTIONS.map(option => ({
      id: 'asset-token-type-' + option.key,
      className: 'asset-kind-icon asset-token-type-icon asset-token-type-' + option.key,
      title: option.label,
      active: currentData.tokenType === option.tokenType,
      action: () => applyTransferableTokenType(element, this._modeling, option.tokenType)
    }))
  ];
};

AssetTypePopupProvider.prototype.getEntries = function() {
  return [];
};

AssetTypePopupProvider.prototype.register = function() {
  this._popupMenu.registerProvider('asset-type-provider', this);
};
