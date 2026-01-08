import icon from '../../../../../assets/token.svg'

export default class AssetTaskPaletteProvider{
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
        'shape', { type: 'bpmn:Task' },
      )

      create.start(event, serviceTaskShape)
    }

    return {
      'create-test-data': {
        group: 'activity',
        title: '创建 NFT资产',
        imageUrl: icon,
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
]