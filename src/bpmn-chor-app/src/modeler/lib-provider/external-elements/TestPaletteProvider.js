import emailIcon from '../../../assets/email.svg'
import dataIcon from '../../../assets/icons/external-data.svg'
import computeTaskIcon from '../../../assets/icons/compute-task.svg'
import groupIcon from '../../../assets/icons/group.svg'

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
      const taskShape = elementFactory.create(
        'shape',
        { type: 'bpmn:BusinessRuleTask' }
      )
      create.start(event, taskShape)
    }
    function startExternalData(event) {
      const taskShape = elementFactory.create(
        'shape',
        {
          type: 'bpmn:ReceiveTask',
        }
      )
      taskShape.businessObject.name = '外部数据元素'
      create.start(event, taskShape)
    }

    function startComputeTask(event) {
      const taskShape = elementFactory.create(
        'shape',
        {
          type: 'bpmn:ScriptTask',
        }
      )
      taskShape.businessObject.name = '计算任务元素'
      create.start(event, taskShape)
    }

    function startCreateGroup(event) {
      const groupShape = elementFactory.create(
        'shape',
        {
          type: 'bpmn:Group',
        }
      )
      create.start(event, groupShape)
    }

    return {
      'create-test-task': {
        group: 'activity',
        title: '创建 businessRule元素',

        imageUrl: emailIcon,
        action: {
          dragstart: startCreate,
          click: startCreate,
        },
      },
      'create-external-data-task': {
        group: 'activity',
        title: '外部数据元素',
        imageUrl: dataIcon,
        action: {
          dragstart: startExternalData,
          click: startExternalData,
        },
      },
      'create-compute-task': {
        group: 'activity',
        title: '计算任务元素',
        imageUrl: computeTaskIcon,
        action: {
          dragstart: startComputeTask,
          click: startComputeTask,
        },
      },
      'create-group': {
        group: 'activity',
        title: '创建分组',
        imageUrl: groupIcon,
        action: {
          dragstart: startCreateGroup,
          click: startCreateGroup,
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
