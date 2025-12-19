/**
 * 数据元素调色板提供者
 * 在左侧调色板添加 DataObjectReference 元素
 */
export default class DataPaletteProvider {
  constructor(palette, create, elementFactory, translate) {
    this._create = create;
    this._elementFactory = elementFactory;
    this._translate = translate;

    palette.registerProvider(this);
  }

  getPaletteEntries(element) {
    const {
      _create: create,
      _elementFactory: elementFactory,
      _translate: translate,
    } = this;

    function createDataObject(event) {
      const shape = elementFactory.createShape({
        type: 'bpmn:DataObjectReference'
      });
      create.start(event, shape);
    }

    return {
      'create.data-object': {
        group: 'data-object',
        className: 'bpmn-icon-data-object',
        title: translate('Create DataObjectReference'),
        action: {
          dragstart: createDataObject,
          click: createDataObject,
        },
      },
    };
  }
}

DataPaletteProvider.$inject = [
  'palette',
  'create',
  'elementFactory',
  'translate',
];
