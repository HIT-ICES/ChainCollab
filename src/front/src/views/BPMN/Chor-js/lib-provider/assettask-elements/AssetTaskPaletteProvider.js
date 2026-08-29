import { ensureAssetOperation } from '../../utils/assetExtension';

export default class AssetTaskPaletteProvider{
  constructor(palette, create, elementFactory, moddle) {

    this.create = create
    this.elementFactory = elementFactory
    this.moddle = moddle
    palette.registerProvider(this)
  }

  // 这个函数就是绘制palette的核心
  getPaletteEntries(element) {
    const elementFactory = this.elementFactory
    const create = this.create
    const moddle = this.moddle

    function startCreate(event) {
      const assetTaskShape = elementFactory.createShape({
        type: 'bpmn:ChoreographyTask'
      });

      ensureAssetOperation(assetTaskShape, moddle);
      create.start(event, assetTaskShape);
    }

    return {
      'create.asset-task': {
        group: 'choreography',
        className: 'choreo-icon-choreography-task',
        title: 'Create AssetTask',
        action: {
          dragstart: startCreate,
          click: startCreate,
        },
      },
    }
  }
}

AssetTaskPaletteProvider.$inject = [
  'palette',
  'create',
  'elementFactory',
  'moddle',
]
