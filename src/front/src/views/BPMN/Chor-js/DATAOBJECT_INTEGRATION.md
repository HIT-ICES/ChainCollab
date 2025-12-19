# DataObject 元素集成技术文档

## 概述

本文档记录了在 chor-js (Choreography Diagram Editor) 中集成 BPMN DataObjectReference 元素的完整实现方案。

### 实现功能

- ✅ 调色板添加 DataObject 图标，支持拖拽创建
- ✅ DataObject 和 ChoreographyActivity 之间的连接支持
  - DataObject → ChoreographyActivity = `DataInputAssociation`
  - ChoreographyActivity → DataObject = `DataOutputAssociation`
- ✅ 上下文菜单（Context Menu）支持连接和删除
- ✅ 属性面板支持编辑 DataObject 的 name 和 state 属性
- ✅ 防止 ChoreographyActivity 在连接后变为 Activity（关键问题修复）

---

## 文件结构

### 新增文件

```
lib-provider/
└── data-elements/                              [新建目录]
    ├── index.js                                [新建] 模块入口
    ├── DataPaletteProvider.js                  [新建] 调色板提供者
    └── DataContextPadProvider.js               [新建] 上下文菜单提供者
```

### 修改文件

```
index.tsx                                       [修改] 注册 DataElementsModule
lib-provider/properties-provider/
└── ChorPropertiesProvider.js                   [修改] 添加 DataObject 属性编辑
chor-js/features/
├── rules/ChoreoRules.js                        [修改] 连接规则
├── modeling/
│   ├── ChoreoModeling.js                       [修改] 重写 connect 方法
│   ├── ChoreoUpdater.js                        [修改] 处理语义父级更新
│   └── behavior/
│       ├── index.js                            [修改] 注册 DataAssociationBehavior
│       └── DataAssociationBehavior.js          [新建] 保护 ChoreographyActivity 完整性
```

---

## 核心实现方案

### 1. 调色板集成 (DataPaletteProvider.js)

**文件位置**: `lib-provider/data-elements/DataPaletteProvider.js`

**实现思路**:
- 使用 bpmn-js 的 `PaletteProvider` 接口
- 创建 `bpmn:DataObjectReference` 类型的元素
- 使用标准 BPMN 图标 `bpmn-icon-data-object`（无需自定义渲染）

**关键代码**:
```javascript
export default class DataPaletteProvider {
  constructor(palette, create, elementFactory, translate) {
    this._create = create;
    this._elementFactory = elementFactory;
    this._translate = translate;
    palette.registerProvider(this);
  }

  getPaletteEntries(element) {
    const { _create: create, _elementFactory: elementFactory, _translate: translate } = this;

    function createDataObject(event) {
      const shape = elementFactory.createShape({ type: 'bpmn:DataObjectReference' });
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

DataPaletteProvider.$inject = ['palette', 'create', 'elementFactory', 'translate'];
```

**技术要点**:
- `type: 'bpmn:DataObjectReference'` 是 BPMN 2.0 标准类型
- bpmn-js 已内置该类型的渲染器，无需额外开发
- 图标使用 `bpmn-font` 中预定义的样式

---

### 2. 上下文菜单 (DataContextPadProvider.js)

**文件位置**: `lib-provider/data-elements/DataContextPadProvider.js`

**实现思路**:
- 为 DataObject 添加"连接"和"删除"按钮
- 为 ChoreographyActivity 添加"连接到 DataObject"按钮
- 使用 `isAny` 工具函数判断元素类型（从 `bpmn-js/lib/features/modeling/util/ModelingUtil` 导入）

**关键代码**:
```javascript
import { assign, isArray } from 'min-dash';
import { is } from 'bpmn-js/lib/util/ModelUtil';
import { isAny } from 'bpmn-js/lib/features/modeling/util/ModelingUtil';

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
    const actions = {};

    // DataObject 的上下文菜单
    if (isAny(element.businessObject, ['bpmn:DataObjectReference', 'bpmn:DataStoreReference'])) {
      function startConnect(event, element) {
        connect.start(event, element);
      }

      assign(actions, {
        'connect': {
          group: 'connect',
          className: 'bpmn-icon-connection-multi',
          title: translate('Connect using DataInputAssociation'),
          action: { click: startConnect, dragstart: startConnect }
        },
        'delete': { /* ... */ }
      });
    }

    // ChoreographyActivity 的上下文菜单
    if (is(element, 'bpmn:ChoreographyActivity')) {
      assign(actions, {
        'connect.data': {
          group: 'connect',
          className: 'bpmn-icon-data-object',
          title: translate('Connect to DataObject'),
          action: { click: startConnect, dragstart: startConnect }
        }
      });
    }

    return actions;
  }
}
```

**技术要点**:
- `isAny` 必须从 `ModelingUtil` 导入，不能从 `ModelUtil` 导入（会报错）
- 连接类型由 `ChoreoRules.canConnect` 自动判断

---

### 3. 属性面板集成 (ChorPropertiesProvider.js)

**文件位置**: `lib-provider/properties-provider/ChorPropertiesProvider.js`

**实现思路**:
- chor-js 使用扩展 `BpmnPropertiesProvider` 的模式，不支持 `registerProvider`
- 直接在 `ChorPropertiesProvider` 中添加 `dataObjectProperties` 方法
- 使用 `entryFactory.textField` 创建属性字段

**关键代码**:
```javascript
// 在 getTabs 方法中添加
if (is(element, 'bpmn:DataObjectReference')) {
  this.dataObjectProperties(detailsGroup, element);
}

// 添加原型方法
ChorPropertiesProvider.prototype.dataObjectProperties = function(group, element) {
  group.entries.push(entryFactory.textField({
    id: 'data-object-state',
    label: 'State',
    modelProperty: 'state',
    get: function(element) {
      const dataObject = element.businessObject.dataObjectRef;
      return { state: dataObject ? (dataObject.state || '') : '' };
    },
    set: function(element, values) {
      const dataObject = element.businessObject.dataObjectRef;
      if (dataObject) {
        return cmdHelper.updateBusinessObject(element, dataObject, {
          state: values.state || ''
        });
      }
    }
  }));
};
```

**技术要点**:
- DataObjectReference 的实际数据存储在 `businessObject.dataObjectRef` 中
- 使用 `cmdHelper.updateBusinessObject` 确保修改可撤销

---

### 4. 连接规则 (ChoreoRules.js)

**文件位置**: `chor-js/features/rules/ChoreoRules.js`

**实现思路**:
- 在 `canConnect` 方法中，**规则顺序至关重要**：
  1. **先定义允许的规则**（DataObject ↔ ChoreographyActivity）
  2. **再定义阻止的规则**（DataObject + SequenceFlow）
- 允许 DataInputAssociation 和 DataOutputAssociation

**关键代码**:
```javascript
ChoreoRules.prototype.canConnect = function (source, target, connection) {
  // 第一步: 允许 DataAssociation 连接到 ChoreographyActivity
  if (is(source, 'bpmn:DataObjectReference') || is(source, 'bpmn:DataStoreReference')) {
    if (is(target, 'bpmn:ChoreographyActivity')) {
      return { type: 'bpmn:DataInputAssociation' };
    }
  }
  if (is(target, 'bpmn:DataObjectReference') || is(target, 'bpmn:DataStoreReference')) {
    if (is(source, 'bpmn:ChoreographyActivity')) {
      return { type: 'bpmn:DataOutputAssociation' };
    }
  }

  // 第二步: 阻止其他类型的连接（如 SequenceFlow）
  if (is(source, 'bpmn:DataObjectReference') || is(source, 'bpmn:DataStoreReference') ||
      is(target, 'bpmn:DataObjectReference') || is(target, 'bpmn:DataStoreReference')) {
    if (connection && is(connection, 'bpmn:DataAssociation')) {
      return true; // 允许重连已有的 DataAssociation
    }
    return false; // 阻止其他连接类型
  }

  // 其他规则...
  return BpmnRules.prototype.canConnect.call(this, source, target, connection);
};
```

**技术要点**:
- **规则顺序错误会导致允许规则被阻止规则覆盖**
- 返回 `{ type: 'bpmn:DataInputAssociation' }` 指定连接类型
- 阻止 SequenceFlow 连接到 DataObject

---

### 5. 连接预处理 (ChoreoModeling.js)

**文件位置**: `chor-js/features/modeling/ChoreoModeling.js`

**实现思路**:
- 重写 `connect` 方法，在调用父类方法前预处理
- 为 ChoreographyActivity 预先创建 `dataInputAssociations` 和 `dataOutputAssociations` 数组
- 添加详细日志便于调试

**关键代码**:
```javascript
import { is } from 'bpmn-js/lib/util/ModelUtil';

ChoreoModeling.prototype.connect = function(source, target, attrs, hints) {
  const isDataAssociation =
    (is(source, 'bpmn:DataObjectReference') || is(source, 'bpmn:DataStoreReference')) &&
    is(target, 'bpmn:ChoreographyActivity') ||
    (is(target, 'bpmn:DataObjectReference') || is(target, 'bpmn:DataStoreReference')) &&
    is(source, 'bpmn:ChoreographyActivity');

  if (isDataAssociation) {
    console.log('[ChoreoModeling.connect] BEFORE connection:');
    console.log('  Source:', source.type, source.businessObject.$type);
    console.log('  Target:', target.type, target.businessObject.$type);

    // CRITICAL: ChoreographyActivity 不原生支持 DataAssociation
    // 需要在 bpmn-js 尝试添加之前准备好数组
    if (is(source, 'bpmn:ChoreographyActivity')) {
      if (!source.businessObject.dataOutputAssociations) {
        source.businessObject.dataOutputAssociations = [];
      }
    }
    if (is(target, 'bpmn:ChoreographyActivity')) {
      if (!target.businessObject.dataInputAssociations) {
        target.businessObject.dataInputAssociations = [];
      }
    }
  }

  // 调用父类方法
  const result = BpmnModeling.prototype.connect.call(this, source, target, attrs, hints);

  if (isDataAssociation) {
    console.log('[ChoreoModeling.connect] AFTER connection:');
    // ... 日志
  }

  return result;
};
```

**技术要点**:
- ChoreographyActivity 继承自 FlowNode，不继承自 Activity
- Activity 类原生支持 DataAssociation，但 ChoreographyActivity 不支持
- 必须手动准备数组，否则 bpmn-js 会尝试 push 到 undefined

---

### 6. 语义模型更新 (ChoreoUpdater.js) - 核心修复

**文件位置**: `chor-js/features/modeling/ChoreoUpdater.js`

**问题背景**:
连接 DataObject 后，新创建的 ChoreographyTask 会变为普通 Activity，失去 participant bands。

**根本原因**:
1. `updateSemanticParent` 被调用时，`sourceRef` 和 `targetRef` 尚未设置（值为 `undefined`）
2. 代码无法判断这是 ChoreographyActivity 相关的 DataAssociation
3. 调用了 `BpmnUpdater.prototype.updateSemanticParent`，导致数组 push 错误
4. 错误导致 ChoreographyActivity 的结构被破坏

**解决方案**:
- 检查 `newParent` 是否为 ChoreographyActivity（而不是依赖 sourceRef/targetRef）
- 手动处理所有数组操作，**完全绕过 BpmnUpdater**
- 在 newParent 上直接创建并填充 dataInputAssociations/dataOutputAssociations 数组

**关键代码**:
```javascript
ChoreoUpdater.prototype.updateSemanticParent = function (businessObject, newParent, visualParent) {
  if (!is(businessObject, 'bpmn:Participant') && !is(businessObject, 'bpmn:Message')) {
    if (is(businessObject, 'bpmn:DataAssociation')) {
      console.log('[ChoreoUpdater.updateSemanticParent] DataAssociation detected');

      const sourceRef = businessObject.sourceRef;
      const targetRef = businessObject.targetRef;

      console.log('  sourceRef:', sourceRef?.$type);
      console.log('  targetRef:', targetRef?.$type);

      // CRITICAL: 检查 newParent 是否为 ChoreographyActivity
      // sourceRef/targetRef 在此时可能尚未设置
      const involvesChoreography =
        (sourceRef && is(sourceRef, 'bpmn:ChoreographyActivity')) ||
        (targetRef && is(targetRef, 'bpmn:ChoreographyActivity')) ||
        (visualParent?.source && is(visualParent.source, 'bpmn:ChoreographyActivity')) ||
        (visualParent?.target && is(visualParent.target, 'bpmn:ChoreographyActivity')) ||
        is(newParent, 'bpmn:ChoreographyActivity'); // ← 关键修复

      if (involvesChoreography) {
        console.log('[ChoreoUpdater.updateSemanticParent] Handling manually, NOT calling BpmnUpdater');

        // 添加到父容器的 flowElements
        if (newParent) {
          if (!newParent.flowElements) {
            newParent.flowElements = [];
          }
          if (!newParent.flowElements.includes(businessObject)) {
            newParent.flowElements.push(businessObject);
          }
        }

        // CRITICAL: 在 ChoreographyActivity 上准备数组
        if (is(newParent, 'bpmn:ChoreographyActivity')) {
          // DataInputAssociation: ChoreographyActivity 是目标
          if (is(businessObject, 'bpmn:DataInputAssociation')) {
            if (!newParent.dataInputAssociations) {
              newParent.dataInputAssociations = [];
            }
            if (!newParent.dataInputAssociations.includes(businessObject)) {
              newParent.dataInputAssociations.push(businessObject);
            }
          }

          // DataOutputAssociation: ChoreographyActivity 是源
          if (is(businessObject, 'bpmn:DataOutputAssociation')) {
            if (!newParent.dataOutputAssociations) {
              newParent.dataOutputAssociations = [];
            }
            if (!newParent.dataOutputAssociations.includes(businessObject)) {
              newParent.dataOutputAssociations.push(businessObject);
            }
          }
        }

        // 如果 sourceRef/targetRef 已设置，也添加到它们的数组中
        if (is(businessObject, 'bpmn:DataOutputAssociation') && sourceRef &&
            is(sourceRef, 'bpmn:ChoreographyActivity')) {
          if (!sourceRef.dataOutputAssociations) {
            sourceRef.dataOutputAssociations = [];
          }
          if (!sourceRef.dataOutputAssociations.includes(businessObject)) {
            sourceRef.dataOutputAssociations.push(businessObject);
          }
        }

        if (is(businessObject, 'bpmn:DataInputAssociation') && targetRef &&
            is(targetRef, 'bpmn:ChoreographyActivity')) {
          if (!targetRef.dataInputAssociations) {
            targetRef.dataInputAssociations = [];
          }
          if (!targetRef.dataInputAssociations.includes(businessObject)) {
            targetRef.dataInputAssociations.push(businessObject);
          }
        }

        // 设置父级引用
        businessObject.$parent = newParent;

        console.log('[ChoreoUpdater.updateSemanticParent] Manual handling complete, returning');
        // 不调用 BpmnUpdater，直接返回
        return;
      }

      console.log('[ChoreoUpdater.updateSemanticParent] NOT involving Choreography, will call BpmnUpdater');
    }

    // 其他情况使用默认行为
    BpmnUpdater.prototype.updateSemanticParent.call(this, businessObject, newParent, visualParent);
  }
};
```

**技术要点**:
- **关键修复**: `is(newParent, 'bpmn:ChoreographyActivity')` 检查
- 在 updateSemanticParent 调用时，sourceRef/targetRef 通常为 undefined
- 但 newParent 参数始终可用且正确
- 完全绕过 BpmnUpdater 避免其内部逻辑破坏 ChoreographyActivity 结构

---

### 7. 完整性保护 (DataAssociationBehavior.js)

**文件位置**: `chor-js/features/modeling/behavior/DataAssociationBehavior.js`

**实现思路**:
- 使用 `CommandInterceptor` 监听 `connection.create` 和 `connection.reconnect` 事件
- 在连接创建后（postExecuted），确保 ChoreographyActivity 的必要属性存在
- 防止意外情况导致属性丢失

**关键代码**:
```javascript
import inherits from 'inherits';
import CommandInterceptor from 'diagram-js/lib/command/CommandInterceptor';
import { is } from 'bpmn-js/lib/util/ModelUtil';

export default function DataAssociationBehavior(injector) {
  injector.invoke(CommandInterceptor, this);

  // 连接创建后保护 ChoreographyActivity
  this.postExecuted('connection.create', function (event) {
    const context = event.context;
    const connection = context.connection;
    const source = context.source;
    const target = context.target;

    if (is(connection, 'bpmn:DataAssociation')) {
      console.log('[DataAssociationBehavior] postExecuted connection.create');

      if (is(source, 'bpmn:ChoreographyActivity')) {
        ensureChoreographyActivity(source);
      }
      if (is(target, 'bpmn:ChoreographyActivity')) {
        ensureChoreographyActivity(target);
      }
    }
  });

  // 重连时也保护
  this.postExecuted('connection.reconnect', function (event) {
    const context = event.context;
    const connection = context.connection;
    const source = context.newSource || context.source;
    const target = context.newTarget || context.target;

    if (is(connection, 'bpmn:DataAssociation')) {
      if (is(source, 'bpmn:ChoreographyActivity')) {
        ensureChoreographyActivity(source);
      }
      if (is(target, 'bpmn:ChoreographyActivity')) {
        ensureChoreographyActivity(target);
      }
    }
  });
}

function ensureChoreographyActivity(shape) {
  const businessObject = shape.businessObject;

  if (is(businessObject, 'bpmn:ChoreographyActivity')) {
    // 确保 participantRef 数组存在
    if (!businessObject.participantRef) {
      businessObject.participantRef = [];
    }

    // 确保 bandShapes 数组存在
    if (!shape.bandShapes) {
      shape.bandShapes = [];
    }
  }
}

DataAssociationBehavior.$inject = ['injector'];
inherits(DataAssociationBehavior, CommandInterceptor);
```

**技术要点**:
- `postExecuted` 在命令执行后触发，确保连接已创建
- `participantRef` 是 ChoreographyActivity 的核心属性
- `bandShapes` 是 chor-js 特有的视觉元素数组

**注册方式**:
在 `chor-js/features/modeling/behavior/index.js` 中注册：
```javascript
import DataAssociationBehavior from './DataAssociationBehavior';

export default {
  __init__: [
    'createChoreoTaskBehavior',
    // ... 其他 behaviors
    'dataAssociationBehavior'  // ← 添加
  ],
  // ...
  dataAssociationBehavior: ['type', DataAssociationBehavior]
};
```

---

### 8. 模块集成 (index.tsx)

**文件位置**: `index.tsx`

**修改内容**:
```javascript
// 第 12 行附近：导入模块
import DataElementsModule from './lib-provider/data-elements';

// 第 294 行附近：注册模块
modeler.current = new ChoreoModeler({
  container: modelerRef.current,
  keyboard: { bindTo: document },
  propertiesPanel: {
    parent: propertiesPanelRef.current,
  },
  additionalModules: [
    PropertiesPanelModule,
    PropertiesProviderModule,
    TestPaletteProvider,
    DataElementsModule,  // ← 添加此行
  ],
});
```

---

## 关键技术决策

### 1. 为什么不需要自定义渲染器？

**原因**:
- bpmn-js 的 `BpmnRenderer` 已内置 `DataObjectReference` 的渲染逻辑
- chor-js 的 `ChoreoRenderer.canRender()` 只处理编排特定元素：
  - `bpmn:ChoreographyActivity`
  - `bpmn:Participant`（participant bands）
  - `bpmn:Message`
- 其他元素自动回退到 bpmn-js 的标准渲染器

**验证代码** (`chor-js/draw/ChoreoRenderer.js`):
```javascript
ChoreoRenderer.prototype.canRender = function(element) {
  return (
    isChoreoActivity(element) ||
    is(element, 'bpmn:Participant') ||
    is(element, 'bpmn:Message')
  );
};
```

DataObjectReference 不在上述列表中，因此使用 bpmn-js 默认渲染。

---

### 2. 为什么规则顺序很重要？

**问题场景**:
用户从 ChoreographyTask 使用 SequenceFlow 连接到 DataObject 时报错。

**原因分析**:
如果先定义阻止规则，后定义允许规则：
```javascript
// 错误顺序
if (is(source, 'bpmn:DataObjectReference') || ...) {
  return false; // 阻止所有连接
}

if (is(target, 'bpmn:ChoreographyActivity')) {
  return { type: 'bpmn:DataInputAssociation' }; // 永远不会执行到这里
}
```

**正确顺序**:
1. 先检查并允许 DataAssociation（特例）
2. 再阻止其他连接类型（通用规则）

---

### 3. ChoreographyActivity vs Activity 的区别

**类继承关系**:
```
FlowNode (抽象基类)
├── Activity
│   ├── Task
│   ├── SubProcess
│   └── CallActivity
└── ChoreographyActivity
    ├── ChoreographyTask
    ├── SubChoreography
    └── CallChoreography
```

**关键差异**:
- `Activity` 原生支持 `dataInputAssociations` 和 `dataOutputAssociations`
- `ChoreographyActivity` 不继承自 Activity，不原生支持这些属性
- 需要手动添加这些属性到 ChoreographyActivity

**BPMN 规范**:
根据 BPMN 2.0 规范，ChoreographyActivity 理论上可以关联数据对象，但规范未明确定义实现方式。bpmn-js 的实现中，这些属性不是 ChoreographyActivity 的原生属性。

---

### 4. 为什么不能依赖 sourceRef/targetRef？

**时序问题**:
```
1. 用户拖拽连接: DataObject → ChoreographyTask
2. connect.start 事件触发
3. BpmnModeling.createConnection 创建 DataInputAssociation businessObject
4. 此时 sourceRef 和 targetRef 尚未设置 ← 问题所在
5. updateSemanticParent 被调用
6. 之后 sourceRef/targetRef 才被设置
```

**解决方案**:
使用 `newParent` 参数判断：
- `newParent` 在 updateSemanticParent 调用时始终可用
- 代表 DataAssociation 将被添加到哪个父元素
- 如果 newParent 是 ChoreographyActivity，则需要特殊处理

---

## 调试技巧

### 控制台日志

实现中添加了详细的调试日志，按以下顺序触发：

**创建 ChoreographyTask**:
```
[CreateChoreoTaskBehavior] preExecuted shape.create
  Shape type: bpmn:ChoreographyTask
  BusinessObject type: bpmn:ChoreographyTask
  Has name: undefined

[CreateChoreoTaskBehavior] postExecuted shape.create START
  bandShapes exists: false
  participantRef length: undefined

[CreateChoreoTaskBehavior] postExecuted shape.create END
  bandShapes length: 2
  participantRef length: 2
```

**连接 DataObject 到 ChoreographyTask**:
```
[ChoreoModeling.connect] BEFORE connection:
  Source: bpmn:DataObjectReference
  Target: bpmn:ChoreographyTask
  Target bandShapes: 2
  Target participantRef: 2

[ChoreoUpdater.updateSemanticParent] DataAssociation detected:
  businessObject type: bpmn:DataInputAssociation
  newParent: bpmn:ChoreographyTask
  visualParent: undefined
  sourceRef: undefined
  targetRef: undefined
  involvesChoreography: true  ← 修复后应为 true

[ChoreoUpdater.updateSemanticParent] Handling manually, NOT calling BpmnUpdater
[ChoreoUpdater.updateSemanticParent] Manual handling complete, returning

[DataAssociationBehavior] postExecuted connection.create
  Source bandShapes: 2
  Target bandShapes: 2

[ChoreoModeling.connect] AFTER connection:
  Target bandShapes: 2
  Target participantRef: 2
```

### 常见错误信息

**1. TypeError: Cannot read properties of undefined (reading 'push')**
- **原因**: BpmnUpdater 尝试 push 到不存在的数组
- **解决**: 在 ChoreoUpdater.updateSemanticParent 中绕过 BpmnUpdater

**2. The requested module does not provide an export named 'isAny'**
- **原因**: 从错误的模块导入 `isAny`
- **解决**: 从 `bpmn-js/lib/features/modeling/util/ModelingUtil` 导入，不是 `ModelUtil`

**3. propertiesPanel.registerProvider is not a function**
- **原因**: chor-js 不支持 `registerProvider` 模式
- **解决**: 直接在 `ChorPropertiesProvider` 中添加方法

---

## 扩展功能

### 未来可添加的功能

#### 1. DataStoreReference（数据存储）
在 `DataPaletteProvider.js` 中添加：
```javascript
function createDataStore(event) {
  const shape = elementFactory.createShape({ type: 'bpmn:DataStoreReference' });
  create.start(event, shape);
}

return {
  'create.data-object': { /* 现有代码 */ },
  'create.data-store': {
    group: 'data-object',
    className: 'bpmn-icon-data-store',
    title: translate('Create DataStoreReference'),
    action: {
      dragstart: createDataStore,
      click: createDataStore,
    },
  },
};
```

#### 2. 数据对象集合标记
在属性面板添加复选框：
```javascript
entryFactory.checkbox({
  id: 'data-object-collection',
  label: 'Is Collection',
  modelProperty: 'isCollection',
  get: function(element) {
    const dataObject = element.businessObject.dataObjectRef;
    return { isCollection: dataObject ? dataObject.isCollection : false };
  },
  set: function(element, values) {
    const dataObject = element.businessObject.dataObjectRef;
    if (dataObject) {
      return cmdHelper.updateBusinessObject(element, dataObject, {
        isCollection: values.isCollection
      });
    }
  }
})
```

#### 3. 自定义样式
通过 CSS 修改 DataObject 外观：
```css
.djs-element[data-element-id^="DataObjectReference_"] .djs-visual > rect {
  fill: #e3f2fd !important;
  stroke: #1976d2 !important;
  stroke-width: 2px !important;
}
```

---

## 测试清单

### 基础功能
- ✅ 调色板显示 DataObject 图标
- ✅ 拖拽创建 DataObject
- ✅ DataObject 正确显示在画布上

### 连接功能
- ✅ DataObject → ChoreographyTask 创建 DataInputAssociation
- ✅ ChoreographyTask → DataObject 创建 DataOutputAssociation
- ✅ 连接线显示虚线样式
- ✅ 可以创建多个关联（一个 Activity 连接多个 DataObject）
- ✅ 阻止 SequenceFlow 连接到 DataObject

### ChoreographyActivity 完整性
- ✅ 连接 DataObject 后，ChoreographyTask 保持类型不变
- ✅ 连接后创建新的 ChoreographyTask，仍显示 participant bands
- ✅ participantRef 和 bandShapes 属性保持完整

### 属性编辑
- ✅ 属性面板显示 DataObject 属性
- ✅ 可以编辑名称和状态
- ✅ 更改可撤销（Ctrl+Z）

### XML 导入导出
- ✅ 导出 XML 符合 BPMN 2.0 标准
- ✅ 重新导入 XML 正确恢复 DataObject 和关联

---

## 本次修复总结（导入/导出稳定性）

本次修复聚焦 DataObject / DataAssociation 的导入导出一致性，解决了下载报错、导入不显示、关联线丢失等问题：

- **导出丢关联**：连接后将 `DataInputAssociation` / `DataOutputAssociation` 挂载到 `ChoreographyActivity`，并设置 `$parent`，确保多条关联都被序列化。
- **DI 排序补全**：DI 排序遍历纳入 `dataInputAssociations` / `dataOutputAssociations`，防止导出时遗漏关联边。
- **导入缺语义**：当 XML 只有 `BPMNEdge` 时，导入阶段可根据边端点反推并创建 `DataInputAssociation` / `DataOutputAssociation` 语义对象。
- **端点解析容错**：允许端点轻微偏移，提高关联边的恢复成功率。
- **缺失 DI 容错**：对缺 DI 元素/边给出警告并跳过，避免导入中断。

### 边界情况
- ✅ 删除 Activity 时关联的 DataAssociation 自动删除
- ✅ 删除 DataObject 时关联自动删除
- ✅ 上下文菜单正确显示

---

## 参考资料

### BPMN 2.0 规范
- [BPMN 2.0 Specification](https://www.omg.org/spec/BPMN/2.0/)
- DataObject: BPMN 2.0 §10.2
- DataAssociation: BPMN 2.0 §10.2.4

### bpmn-js 文档
- [bpmn-js Examples](https://github.com/bpmn-io/bpmn-js-examples)
- [Custom Elements](https://github.com/bpmn-io/bpmn-js-examples/tree/master/custom-elements)
- [Properties Panel Extension](https://github.com/bpmn-io/bpmn-js-examples/tree/master/properties-panel-extension)

### chor-js 源码
- [chor-js GitHub](https://github.com/bptlab/chor-js)
- Renderer: `chor-js/draw/ChoreoRenderer.js`
- Rules: `chor-js/features/rules/ChoreoRules.js`
- Modeling: `chor-js/features/modeling/`

---

## 版本历史

| 版本 | 日期 | 描述 |
|------|------|------|
| 1.0.0 | 2024-12 | 初始实现：调色板、上下文菜单、属性面板 |
| 1.1.0 | 2024-12 | 修复连接规则，支持 DataAssociation |
| 1.2.0 | 2024-12 | 修复 ChoreographyTask 转换为 Activity 的问题 |
| 1.3.0 | 2024-12 | 完善 ChoreoUpdater，检查 newParent 参数 |

---

## 贡献者

- 实现: Claude (Anthropic)
- 需求与测试: 用户

---

## 许可证

本实现遵循 chor-js 项目的许可证（MIT License）。

---

**文档完成日期**: 2024-12-19
