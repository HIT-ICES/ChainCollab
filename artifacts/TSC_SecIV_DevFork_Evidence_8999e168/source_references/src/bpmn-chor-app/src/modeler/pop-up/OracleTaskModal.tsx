// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { Modal, Input, Typography } from 'antd';

const { Text } = Typography;

const OracleTaskModal = ({ dataElementId, open: isModalOpen, onClose }) => {
  const modeler = window.bpmnjs;
  const elementRegistry = modeler.get('elementRegistry');
  const commandStack = modeler.get('commandStack');
  const eventBus = modeler.get('eventBus');
  const shape = elementRegistry.get(dataElementId);
  const taskType = shape?.businessObject?.$type;
  const isExternal = taskType === 'bpmn:ReceiveTask';
  const isCompute = taskType === 'bpmn:ScriptTask';

  const [name, setName] = useState('');
  const [dataSource, setDataSource] = useState('');
  const [computeScript, setComputeScript] = useState('');

  useEffect(() => {
    if (!isModalOpen || !shape) {
      return;
    }
    setName(shape.businessObject.name || '');
    const doc = shape.businessObject.documentation?.[0];
    if (doc?.text) {
      try {
        const payload = JSON.parse(doc.text);
        setDataSource(payload.dataSource || '');
        setComputeScript(payload.computeScript || '');
      } catch (e) {
        setDataSource('');
        setComputeScript('');
      }
    } else {
      setDataSource('');
      setComputeScript('');
    }
  }, [isModalOpen, dataElementId]);

  const handleOk = () => {
    const payload = {
      oracleTaskType: isExternal ? 'external-data' : 'compute-task',
      dataSource: dataSource || '',
      computeScript: computeScript || ''
    };
    commandStack.execute('element.updateProperties', {
      element: shape,
      properties: {
        documentation: [
          modeler._moddle.create('bpmn:Documentation', {
            text: JSON.stringify(payload)
          })
        ]
      }
    });
    commandStack.execute('element.updateLabel', {
      element: shape,
      newLabel: name || (isExternal ? '外部数据元素' : '计算任务元素')
    });
    eventBus.fire('element.changed', { element: shape });
    onClose && onClose(true);
  };

  const handleCancel = () => {
    onClose && onClose(false);
  };

  return (
    <Modal
      title={isExternal ? '外部数据元素配置' : '计算任务元素配置'}
      open={isModalOpen}
      onOk={handleOk}
      onCancel={handleCancel}
      centered
      width={680}
      styles={{
        header: { borderBottom: '1px solid #e2e8f0', padding: '16px 24px' },
        body: { padding: '12px 24px 24px', background: '#f8fafc' },
        footer: { borderTop: 'none', padding: '16px 24px 24px' }
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <Text type="secondary" strong>任务名称</Text>
          <Input
            value={name}
            placeholder={isExternal ? '外部数据元素' : '计算任务元素'}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        {isExternal ? (
          <div>
            <Text type="secondary" strong>数据源</Text>
            <Input
              value={dataSource}
              placeholder="oracle://source 或 https://..."
              onChange={(e) => setDataSource(e.target.value)}
            />
          </div>
        ) : null}
        {isCompute ? (
          <div>
            <Text type="secondary" strong>计算脚本/表达式</Text>
            <Input.TextArea
              value={computeScript}
              placeholder="输入计算规则或脚本"
              autoSize={{ minRows: 4, maxRows: 10 }}
              onChange={(e) => setComputeScript(e.target.value)}
            />
          </div>
        ) : null}
      </div>
    </Modal>
  );
};

export default OracleTaskModal;
