import * as React from 'react';
import { Modal, Input, Select } from 'antd';

export default function FixedFieldsModal({
  dataElementId,    // BpmnJS 元素 id
  open: isModalOpen,
  onClose
}) {
  // 拿到 bpmnjs modeler 实例
  const modeler = window.bpmnjs;
  const elementRegistry = modeler.get('elementRegistry');
  const commandStack = modeler.get('commandStack');
  const shape = elementRegistry.get(dataElementId);

  // 定义 5 个字段的状态
  const [elementName, setElementName] = React.useState('');
  const [caller, setCaller] = React.useState('');
  const [assetType, setAssetType] = React.useState('');
  const [operation, setOperation] = React.useState('');
  const [callee, setCallee] = React.useState([]); // 现在是字符串数组

  // 从 BPMN 里读数据到 state
  const loadDataFromBPMN = () => {
    if (!shape) return;

    setElementName(shape.businessObject.name || '');

    const defaultData = {
      caller:    '',
      assetType: '',
      operation: '',
      callee:    []
    };

    if (
      Array.isArray(shape.businessObject.documentation) &&
      shape.businessObject.documentation.length > 0
    ) {
      try {
        const txt = shape.businessObject.documentation[0].text;
        const parsed = JSON.parse(txt);
        const {
          caller:    callerVal    = defaultData.caller,
          assetType: assetTypeVal = defaultData.assetType,
          operation: operationVal = defaultData.operation,
          callee:    calleeVal    = defaultData.callee
        } = parsed;

        setCaller(callerVal);
        setAssetType(assetTypeVal);
        setOperation(operationVal);

        if (Array.isArray(calleeVal)) {
          setCallee(calleeVal);
        } else if (typeof calleeVal === 'string') {
          setCallee(calleeVal ? [calleeVal] : []);
        } else {
          setCallee([]);
        }
      } catch {
        setCaller(defaultData.caller);
        setAssetType(defaultData.assetType);
        setOperation(defaultData.operation);
        setCallee(defaultData.callee);
      }
    } else {
      setCaller(defaultData.caller);
      setAssetType(defaultData.assetType);
      setOperation(defaultData.operation);
      setCallee(defaultData.callee);
    }
  };

  React.useEffect(() => {
    loadDataFromBPMN();
  }, [shape]);

  // 把 state 写回 BPMN
  const updateDataToBPMN = () => {
    if (!shape) return;

    // 更新 Label
    commandStack.execute('element.updateLabel', {
      element:  shape,
      newLabel: elementName || shape.businessObject.name
    });

    // 构造 JSON
    const uploadData = {
      caller:    caller || '',
      assetType: assetType || '',
      operation: operation || '',
      callee:    Array.isArray(callee) ? callee : []
    };

    commandStack.execute('element.updateProperties', {
      element: shape,
      properties: {
        documentation: [
          modeler._moddle.create('bpmn:Documentation', {
            text: JSON.stringify(uploadData, null, 2)
          })
        ]
      }
    });
  };

  // 点击确定/取消
  const handleOk = () => {
    updateDataToBPMN();
    onClose(true);
  };
  const handleCancel = () => onClose(false);

  return (
    <Modal
      title={`编辑元素 ${dataElementId} 的固定字段`}
      open={isModalOpen}
      onOk={handleOk}
      onCancel={handleCancel}
      width={600}
    >
      {/* 1. 元素名字 */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>elementName：</label>
        <Input
          value={elementName}
          onChange={e => setElementName(e.target.value)}
        />
      </div>

      {/* 2. 调用者 */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>caller：</label>
        <Input
          value={caller}
          onChange={e => setCaller(e.target.value)}
        />
      </div>

      {/* 3. 资产类型 */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>assetType：</label>
        <Select
          value={assetType}
          onChange={value => setAssetType(value)}
          allowClear
          style={{ width: '100%' }}
        >
          <Select.Option value="分发型">分发型</Select.Option>
          <Select.Option value="转移型">转移型</Select.Option>
          <Select.Option value="增值型">增值型</Select.Option>
        </Select>
      </div>

      {/* 4. 操作 */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>operation：</label>
        <Input
          value={operation}
          onChange={e => setOperation(e.target.value)}
        />
      </div>

      {/* 5. 被调用者（callee），tags 模式 + 关闭下拉 */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>callee：</label>
        <Select
          mode="tags"
          open={false}              // 禁用下拉
          value={callee}
          onChange={values => setCallee(values)}
          tokenSeparators={[',']}
          style={{ width: '100%' }}
        />
      </div>
    </Modal>
  );
}
