import * as React from 'react';
import { Modal, Input, Select } from 'antd';

interface FixedFieldsModalProps {
  dataElementId: string;
  open: boolean;
  onClose: (saved: boolean) => void;
}

export default function FixedFieldsModal({
  dataElementId,
  open: isModalOpen,
  onClose,
}: FixedFieldsModalProps) {
  const modeler = window.bpmnjs;
  const elementRegistry = modeler.get('elementRegistry');
  const commandStack = modeler.get('commandStack');
  const shape = elementRegistry.get(dataElementId);

  // Participant 列表去重
  const rawOptions = elementRegistry
    .filter((el: any) => el.businessObject.$type === 'bpmn:Participant')
    .map((el: any) => ({
      value: el.id,
      label: el.businessObject.name || el.id,
    }));
  const participantOptions = Array.from(
    new Map(rawOptions.map(item => [item.label, item])).values()
  );

  // state
  const [elementName, setElementName] = React.useState('');
  const [caller, setCaller] = React.useState('');
  const [assetType, setAssetType] = React.useState('');
  const [operation, setOperation] = React.useState('');
  const [callee, setCallee] = React.useState<string[]>([]);
  const [tokenType, setTokenType] = React.useState('');
  const [tokenName, setTokenName] = React.useState('');
  const [tokenNumber, setTokenNumber] = React.useState(''); // 新增
  const [tokenId, setTokenId] = React.useState('');

  const operationOptions: Record<string, string[]> = {
    '分发型': ['mint', 'burn', 'approve', 'remove approval', 'query'],
    '转移型': ['mint', 'burn', 'Transfer', 'query'],
    '增值型': ['branch', 'merge', 'query'],
  };

  // 从 BPMN 文档加载已有值
  const loadDataFromBPMN = () => {
    if (!shape) return;
    setElementName(shape.businessObject.name || '');
    const doc = shape.businessObject.documentation;
    if (Array.isArray(doc) && doc.length) {
      try {
        const parsed = JSON.parse(doc[0].text);
        setCaller(parsed.caller || '');
        setAssetType(parsed.assetType || '');
        setOperation(parsed.operation || '');
        setTokenType(parsed.tokenType || '');
        setTokenName(parsed.tokenName || '');
        setTokenNumber(parsed.tokenNumber || '');  // 加载 tokenNumber
        setTokenId(parsed.tokenId || '');
        const cv = parsed.callee;
        setCallee(Array.isArray(cv) ? cv : cv ? [cv] : []);
      } catch {
        // ignore
      }
    }
  };

  React.useEffect(() => {
    if (isModalOpen) {
      setElementName('');
      setCaller('');
      setAssetType('');
      setOperation('');
      setTokenType('');
      setTokenName('');
      setTokenNumber('');  // 重置
      setCallee([]);
      setTokenId('');
      loadDataFromBPMN();
    }
  }, [shape, isModalOpen]);

  // 显示条件
  const shouldShowCallee = React.useMemo(() => {
    return (
      (assetType === '转移型' && operation === 'Transfer') ||
      (assetType === '分发型' &&
        (operation === 'approve' || operation === 'remove approval'))
    );
  }, [assetType, operation]);

  const shouldShowTokenName = React.useMemo(() => {
    return assetType === '转移型' && tokenType === 'FT';
  }, [assetType, tokenType]);

  // tokenNumber 也仅在 FT 时显示, 但 operation 为 query 时不显示
  const shouldShowTokenNumber = React.useMemo(() => {
    return shouldShowTokenName && operation !== 'query';
  }, [shouldShowTokenName, operation]);

  const shouldShowTokenId = React.useMemo(() => {
    return !(assetType === '转移型' && tokenType === 'FT');
  }, [assetType, tokenType]);

  // 更新到 BPMN
  const updateDataToBPMN = () => {
    if (!shape) return;

    commandStack.execute('element.updateLabel', {
      element: shape,
      newLabel: elementName || shape.businessObject.name,
    });

    const payload: any = {
      assetType,
      operation,
    };

    if (caller) {
      const o = participantOptions.find(o => o.value === caller);
      payload.caller = o ? o.label : caller;
    }

    if (shouldShowCallee && callee.length) {
      payload.callee = callee.map(id => {
        const o = participantOptions.find(o => o.value === id);
        return o ? o.label : id;
      });
    }

    if (assetType === '转移型') {
      if (tokenType) payload.tokenType = tokenType;
      if (shouldShowTokenName && tokenName) payload.tokenName = tokenName;
      if (shouldShowTokenNumber && tokenNumber) payload.tokenNumber = tokenNumber; // 包含 tokenNumber
    }

    if (shouldShowTokenId && tokenId) {
      payload.tokenId = tokenId;
    }

    commandStack.execute('element.updateProperties', {
      element: shape,
      properties: {
        documentation: [
          modeler._moddle.create('bpmn:Documentation', {
            text: JSON.stringify(payload, null, 2),
          }),
        ],
      },
    });
  };

  return (
    <Modal
      title={`编辑元素 ${dataElementId} 的固定字段`}
      open={isModalOpen}
      onOk={() => { updateDataToBPMN(); onClose(true); }}
      onCancel={() => onClose(false)}
      width={600}
    >
      {/* elementName */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>elementName：</label>
        <Input value={elementName} onChange={e => setElementName(e.target.value)} />
      </div>

      {/* caller */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>caller：</label>
        <Select
          value={caller}
          onChange={setCaller}
          options={participantOptions}
          placeholder="请选择调用者"
          allowClear
          style={{ width: '100%' }}
        />
      </div>

      {/* assetType */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>assetType：</label>
        <Select
          value={assetType}
          onChange={value => {
            setAssetType(value);
            setOperation('');
            setTokenType('');
            setTokenName('');
            setTokenNumber('');  // 清除旧值
            setCallee([]);
            setTokenId('');
          }}
          allowClear
          style={{ width: '100%' }}
        >
          <Select.Option value="分发型">分发型</Select.Option>
          <Select.Option value="转移型">转移型</Select.Option>
          <Select.Option value="增值型">增值型</Select.Option>
        </Select>
      </div>

      {/* operation */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>operation：</label>
        <Select
          value={operation}
          onChange={value => {
            setOperation(value);
            if (!shouldShowCallee) {
              setCallee([]);
            }
          }}
          allowClear
          style={{ width: '100%' }}
        >
          {operationOptions[assetType]?.map(op => (
            <Select.Option key={op} value={op}>
              {op}
            </Select.Option>
          ))}
        </Select>
      </div>

      {/* tokenType */}
      {assetType === '转移型' && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>tokenType：</label>
          <Select
            value={tokenType}
            onChange={value => {
              setTokenType(value);
              setTokenName('');
              setTokenNumber('');
              setTokenId('');
            }}
            allowClear
            style={{ width: '100%' }}
          >
            <Select.Option value="NFT">NFT</Select.Option>
            <Select.Option value="FT">FT</Select.Option>
          </Select>
        </div>
      )}

      {/* tokenName */}
      {shouldShowTokenName && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>tokenName：</label>
          <Input value={tokenName} onChange={e => setTokenName(e.target.value)} />
        </div>
      )}

      {/* tokenNumber */}
      {shouldShowTokenNumber && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>tokenNumber：</label>
          <Input value={tokenNumber} onChange={e => setTokenNumber(e.target.value)} />
        </div>
      )}

      {/* callee */}
      {shouldShowCallee && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>callee：</label>
          <Select
            mode="multiple"
            value={callee}
            onChange={setCallee}
            options={participantOptions}
            placeholder="请选择被调用者"
            allowClear
            style={{ width: '100%' }}
          />
        </div>
      )}

      {/* tokenId */}
      {shouldShowTokenId && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>tokenId：</label>
          <Input value={tokenId} onChange={e => setTokenId(e.target.value)} />
        </div>
      )}
    </Modal>
  );
}
