import icon from '../../icons/font/email.svg'

export default class TestPaletteProvider{
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
        'shape', { type: 'bpmn:BusinessRuleTask' },
      )

      create.start(event, serviceTaskShape)
    }

    return {
      'create-test-task': {
        group: 'activity',
        title: '创建Test businessRule元素',

        imageUrl: icon,
        action: {
          dragstart: startCreate,
          click: startCreate,
        },
      },
    }
  }
}

TestPaletteProvider.$inject = [
  'palette',
  'create',
  'elementFactory',
]