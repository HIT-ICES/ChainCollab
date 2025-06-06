import icon from '../../../../../assets/Dataobject.svg'

export default class DataPaletteProvider{
  // 自定义邮件收发组件
  constructor(palette, create, elementFactory) {

    this.create = create
    this.elementFactory = elementFactory
    palette.registerProvider(this)
  }

  // 这个函数就是绘制palette的核心
  getPaletteEntries(element) {
    const elementFactory = this.elementFactory
    const create = this.create

    function startCreate(event) {
      const serviceTaskShape = elementFactory.create(
        'shape', { type: 'bpmn:DataObject' },
      )

      create.start(event, serviceTaskShape)
    }

    return {
      'create-test-data': {
        group: 'activity',
        title: '创建 data元素',
        imageUrl: icon,
        action: {
          dragstart: startCreate,
          click: startCreate,
        },
      },
    }
  }
}

DataPaletteProvider.$inject = [
  'palette',
  'create',
  'elementFactory',
]