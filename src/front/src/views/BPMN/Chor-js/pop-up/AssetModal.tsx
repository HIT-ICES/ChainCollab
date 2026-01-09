import * as React from 'react';
import { Modal, Input, Select, message } from 'antd';

interface AssetModalProps {
  dataElementId: string;
  open: boolean;
  onClose: (saved: boolean) => void;
}

export default function AssetModal({
  dataElementId,
  open: isModalOpen,
  onClose,
}: AssetModalProps) {
  const modeler = window.bpmnjs;
  const elementRegistry = modeler.get('elementRegistry');
  const commandStack = modeler.get('commandStack');
  const eventBus = modeler.get('eventBus');
  const shape = elementRegistry.get(dataElementId);

  // state
  const [elementName, setElementName] = React.useState('');
  const [assetType, setAssetType] = React.useState('');
  const [tokenType, setTokenType] = React.useState('');
  const [tokenName, setTokenName] = React.useState('');
  const [tokenId, setTokenId] = React.useState('');
  const [originalTokenId, setOriginalTokenId] = React.useState('');
  const [refTokenIds, setRefTokenIds] = React.useState<string[]>([]);

  // tokenId 和 FT tokenName 可选列表
  const [tokenIdOptions, setTokenIdOptions] = React.useState<string[]>([]);
  const [tokenNameOptions, setTokenNameOptions] = React.useState<string[]>([]);

  // 从 BPMN 文档加载已有值
  const loadDataFromBPMN = () => {
    if (!shape) return;
    setElementName(shape.businessObject.name || '');
    const doc = shape.businessObject.documentation;
    if (Array.isArray(doc) && doc.length) {
      try {
        const parsed = JSON.parse(doc[0].text);
        setAssetType(parsed.assetType || '');
        setTokenType(parsed.tokenType || '');
        setTokenName(parsed.tokenName || '');
        const loadedTokenId = parsed.tokenId || '';
        setTokenId(loadedTokenId);
        setOriginalTokenId(loadedTokenId);
        if (parsed.assetType === 'value-added' && Array.isArray(parsed.refTokenIds)) {
          setRefTokenIds(parsed.refTokenIds);
        } else {
          setRefTokenIds([]);
        }
      } catch {
        // ignore parse error
      }
    }
  };

  React.useEffect(() => {
    if (isModalOpen) {
      // 打开时重置并加载
      setElementName('');
      setAssetType('');
      setTokenType('');
      setTokenName('');
      setTokenId('');
      setOriginalTokenId('');
      setRefTokenIds([]);
      loadDataFromBPMN();
    }
  }, [shape, isModalOpen]);

  // ===== 扫描所有 FT tokenName =====
  const scanFTTokenNames = React.useCallback(() => {
    const allElements = elementRegistry.getAll();
    const names = new Set<string>();
    allElements.forEach((el: any) => {
      const docs = el.businessObject.documentation;
      if (Array.isArray(docs) && docs.length) {
        try {
          const p = JSON.parse(docs[0].text);
          // 从 DataObjectReference 扫描 FT tokenName
          if (el.type === 'bpmn:DataObjectReference' &&
              p.assetType === 'transferable' &&
              p.tokenType === 'FT' &&
              p.tokenName) {
            names.add(p.tokenName);
          }
        } catch {
          // ignore
        }
      }
    });
    setTokenNameOptions(Array.from(names));
  }, [elementRegistry]);

  // ===== 扫描 tokenId 并清理旧 tokenId =====
  const scanTokenIdsAndClean = React.useCallback(() => {
    const allElements = elementRegistry.getAll();
    const newTokenIdsSet = new Set<string>();

    // 收集所有 DataObjectReference 的 tokenId
    allElements.forEach((el: any) => {
      const docs = el.businessObject.documentation;
      if (Array.isArray(docs) && docs.length) {
        try {
          const parsed = JSON.parse(docs[0].text);
          // 从 DataObjectReference 扫描 tokenId
          if (el.type === 'bpmn:DataObjectReference' && parsed.tokenId) {
            newTokenIdsSet.add(parsed.tokenId);
          }
        } catch {
          // ignore
        }
      }
    });

    // 更新 tokenIdOptions
    const newTokenIds = Array.from(newTokenIdsSet);
    setTokenIdOptions(prev => {
      const prevSet = new Set(prev);
      const same =
        prevSet.size === newTokenIdsSet.size &&
        newTokenIds.every(id => prevSet.has(id));
      return same ? prev : newTokenIds;
    });
  }, [elementRegistry, commandStack, modeler]);

  // 合并扫描逻辑
  const scanAll = React.useCallback(() => {
    scanTokenIdsAndClean();
    scanFTTokenNames();
  }, [scanTokenIdsAndClean, scanFTTokenNames]);

  React.useEffect(() => {
    // 初次扫描
    scanAll();
    // 监听模型变化，实时重新扫描
    const handler = () => scanAll();
    eventBus.on('commandStack.changed', handler);
    return () => {
      eventBus.off('commandStack.changed', handler);
    };
  }, [eventBus, scanAll]);

  // 更新到 BPMN
  const updateDataToBPMN = () => {
    if (!shape) return;

    commandStack.execute('element.updateLabel', {
      element: shape,
      newLabel: elementName || shape.businessObject.name,
    });

    const payload: any = {
      assetType,
      tokenName
    };

    if (assetType === 'transferable') {
      if (tokenType) payload.tokenType = tokenType;
      if (tokenName) payload.tokenName = tokenName;
    }

    // FT 不需要 tokenId
    if (!(assetType === 'transferable' && tokenType === 'FT') && tokenId) {
      payload.tokenId = tokenId;
    }

    // value-added 需要 refTokenIds
    if (assetType === 'value-added' && refTokenIds.length > 0) {
      payload.refTokenIds = refTokenIds;
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

  const handleOk = () => {
    // 验证 tokenId 是否重复
    if (tokenId && tokenId !== originalTokenId && tokenIdOptions.includes(tokenId)) {
      message.warning('The tokenId already exists. Please choose a different one');
      return;
    }
    updateDataToBPMN();
    onClose(true);
  };

  // 显示条件
  const shouldShowTokenId = React.useMemo(() => {
    return !(assetType === 'transferable' && tokenType === 'FT');
  }, [assetType, tokenType]);

  return (
    <Modal
      title={`Edit Asset Definition for ${dataElementId}`}
      open={isModalOpen}
      onOk={handleOk}
      onCancel={() => onClose(false)}
      width={600}
    >
      {/* 1. elementName */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Element Name:</label>
        <Input value={elementName} onChange={e => setElementName(e.target.value)} />
      </div>

      {/* 2. assetType */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Asset Type:</label>
        <Select
          value={assetType}
          onChange={value => {
            setAssetType(value);
            setTokenType('');
            setTokenName('');
            setTokenId('');
          }}
          allowClear
          style={{ width: '100%' }}
        >
          <Select.Option value="distributive">Distributive</Select.Option>
          <Select.Option value="transferable">Transferable</Select.Option>
          <Select.Option value="value-added">Value-added</Select.Option>
        </Select>
      </div>

      {/* 3. tokenType (仅 transferable) */}
      {assetType === 'transferable' && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token Type:</label>
          <Select
            value={tokenType}
            onChange={value => {
              setTokenType(value);
              setTokenName('');
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

      {/* 4. tokenId (非 FT 类型) */}
      {shouldShowTokenId && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token ID:</label>
          <Input
            value={tokenId}
            onChange={e => setTokenId(e.target.value)}
            placeholder="Enter token ID"
          />
        </div>
      )}

      {/* 5. tokenName */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Token Name:</label>
        <Input
          value={tokenName}
          onChange={e => setTokenName(e.target.value)}
          placeholder="Enter token name"
        />
      </div>

      {/* 6. refTokenIds (仅 value-added) */}
      {assetType === 'value-added' && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Reference Token IDs:</label>
          <Select
            mode="tags"
            value={refTokenIds}
            onChange={setRefTokenIds}
            placeholder="Enter or select token IDs to reference"
            style={{ width: '100%' }}
            options={tokenIdOptions.map(id => ({ label: id, value: id }))}
          />
          <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
            Select existing token IDs or type new ones to create references for value-added assets
          </div>
        </div>
      )}
    </Modal>
  );
}
