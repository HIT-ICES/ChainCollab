import { assign, isArray } from 'min-dash';
import { is } from 'bpmn-js/lib/util/ModelUtil';
import { isAny } from 'bpmn-js/lib/features/modeling/util/ModelingUtil';

/**
 * 数据元素上下文菜单提供者
 * 为 DataObject 和 Task 添加右键菜单（连接、删除功能）
 */
export default class DataContextPadProvider {
  constructor(contextPad, modeling, connect, rules, translate) {
    this._contextPad = contextPad;
    this._modeling = modeling;
    this._connect = connect;
    this._rules = rules;
    this._translate = translate;

    contextPad.registerProvider(this);
  }

  getContextPadEntries(element) {
    const {
      _connect: connect,
      _modeling: modeling,
      _rules: rules,
      _translate: translate,
    } = this;

    const actions = {};

    // For DataObject: add connect and delete
    if (isAny(element.businessObject, [
      'bpmn:DataObjectReference',
      'bpmn:DataStoreReference',
    ])) {
      // 连接功能
      function startConnect(event, element) {
        connect.start(event, element);
      }

      assign(actions, {
        'connect': {
          group: 'connect',
          className: 'bpmn-icon-connection-multi',
          title: translate('Connect using DataAssociation'),
          action: {
            click: startConnect,
            dragstart: startConnect,
          },
        },
      });

      // 删除功能
      let deleteAllowed = rules.allowed('elements.delete', {
        elements: [element],
      });

      if (isArray(deleteAllowed)) {
        deleteAllowed = deleteAllowed[0] === element;
      }

      if (deleteAllowed) {
        assign(actions, {
          'delete': {
            group: 'edit',
            className: 'bpmn-icon-trash',
            title: translate('Remove'),
            action: {
              click: () => modeling.removeElements([element]),
            },
          },
        });
      }
    }

    // For Task: add data connection option
    if (is(element, 'bpmn:Task')) {
      function startConnect(event, element) {
        connect.start(event, element);
      }

      assign(actions, {
        'connect.data': {
          group: 'connect',
          className: 'bpmn-icon-data-object',
          title: translate('Connect to DataObject'),
          action: {
            click: startConnect,
            dragstart: startConnect,
          },
        },
      });
    }

    return actions;
  }
}

DataContextPadProvider.$inject = [
  'contextPad',
  'modeling',
  'connect',
  'rules',
  'translate',
];