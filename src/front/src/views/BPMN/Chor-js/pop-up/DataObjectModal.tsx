import * as React from 'react';
import { Modal, Input, Select, message } from 'antd';

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
  const eventBus = modeler.get('eventBus');
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
  const [tokenNumber, setTokenNumber] = React.useState('');
  const [tokenId, setTokenId] = React.useState('');
  const [originalTokenId, setOriginalTokenId] = React.useState('');
  const [tokenURL, setTokenURL] = React.useState('');
  // 新增：tokenId 和 FT tokenName 可选列表
  const [tokenIdOptions, setTokenIdOptions] = React.useState<string[]>([]);
  const [tokenNameOptions, setTokenNameOptions] = React.useState<string[]>([]);
  //增值型valueadd
  const [refTokenIds, setRefTokenIds] = React.useState<string[]>([]);
  const [refTokenIdOptions, setRefTokenIdOptions] = React.useState<string[]>([]);

  const operationOptions: Record<string, string[]> = {
    'distributive': ['mint', 'burn', 'approve', 'remove approval', 'query'],
    'transferable': ['mint', 'burn', 'Transfer', 'query'],
    'value-added': ['branch', 'merge', 'query'],
  };

  const operationToCallerLabel: Record<string, string> = {
    mint: 'Issuer',              // 发行人
    burn: 'Burner',              // 销毁人
    approve: 'Approver',         // 授权者
    'remove approval': 'Revoker',// 被取消授权者
    query: 'Querier',            // 查询者
    Transfer: 'Sender',          // 转移者
    branch: 'Brancher',          // 分支者
    merge: 'Merger',             // 合并者
  };

  const operationToCalleeLabel: Record<string, string> = {
    mint: 'Receiver',               // 接受者
    burn: 'Burn Target',            // 目标销毁方
    approve: 'Grantee',             // 被授权者
    'remove approval': 'Revoked',   // 被取消授权者
    Transfer: 'Recipient',          // 被转移者
  };

  // 从 BPMN 文档加载已有值
  const loadDataFromBPMN = () => {
    if (!shape) return;
    setElementName(shape.businessObject.name || '');
    const doc = shape.businessObject.documentation;
    if (Array.isArray(doc) && doc.length) {
      try {
        const parsed = JSON.parse(doc[0].text);
        if (parsed.caller) {
          // 在 options 中找 value 以 parsed.caller 为前缀的项（支持 choreo 结构）
          const match = participantOptions.find(opt =>
            opt.value.startsWith(parsed.caller)
          );
          setCaller(match ? match.value : parsed.caller); // 设置 value（完整 ID）
        } else {
          setCaller('');
        }
        setAssetType(parsed.assetType || '');
        setOperation(parsed.operation || '');
        setTokenType(parsed.tokenType || '');
        setTokenName(parsed.tokenName || '');
        setTokenNumber(parsed.tokenNumber || '');
        const loadedTokenId = parsed.tokenId || '';
        setTokenId(loadedTokenId);
        setOriginalTokenId(loadedTokenId);
        setTokenURL(parsed.tokenURL || '');
        if (parsed.assetType === 'value-added' && Array.isArray(parsed.refTokenIds)) {
          setRefTokenIds(parsed.refTokenIds);
        } else {
          setRefTokenIds([]);
        }
        if (Array.isArray(parsed.callee)) {
          const matchedCalleeIds = parsed.callee.map(callerId => {
            const match = participantOptions.find(opt =>
              opt.value.startsWith(callerId)
            );
            return match ? match.value : callerId;
          });
          setCallee(matchedCalleeIds);
        } else {
          setCallee([]);
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
      setCaller('');
      setAssetType('');
      setOperation('');
      setTokenType('');
      setTokenName('');
      setTokenNumber('');
      setCallee(prev => (prev.length ? prev : []));
      setTokenId('');
      setOriginalTokenId('');
      setTokenURL('');
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
          if (p.assetType === 'transferable' && p.tokenType === 'FT' && p.tokenName) {
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

    // 收集所有 mint 操作的 tokenId
    allElements.forEach((el: any) => {
      const docs = el.businessObject.documentation;
      if (Array.isArray(docs) && docs.length) {
        try {
          const parsed = JSON.parse(docs[0].text);
          if ((parsed.operation === 'mint' || parsed.operation === 'branch') && parsed.tokenId) {
            newTokenIdsSet.add(parsed.tokenId);
          }
        } catch {
          // ignore
        }
      }
    });

    // 更新 tokenIdOptions
    setRefTokenIdOptions(Array.from(newTokenIdsSet));
    const newTokenIds = Array.from(newTokenIdsSet);
    setTokenIdOptions(prev => {
      const prevSet = new Set(prev);
      const same =
        prevSet.size === newTokenIdsSet.size &&
        newTokenIds.every(id => prevSet.has(id));
      return same ? prev : newTokenIds;
    });

    // 对所有非 mint 操作且 tokenId 不在新列表中的元素，清理 tokenId
    allElements.forEach((el: any) => {
      const docs = el.businessObject.documentation;
      if (Array.isArray(docs) && docs.length) {
        try {
          const parsed = JSON.parse(docs[0].text);
          if (parsed.tokenId && (parsed.operation === 'mint' || parsed.operation === 'branch') && !newTokenIdsSet.has(parsed.tokenId)) {
            const cleaned = { ...parsed };
            delete cleaned.tokenId;
            commandStack.execute('element.updateProperties', {
              element: el,
              properties: {
                documentation: [
                  modeler._moddle.create('bpmn:Documentation', {
                    text: JSON.stringify(cleaned, null, 2),
                  }),
                ],
              },
            });
          }
        } catch {
          // ignore
        }
      }
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

  // 若当前选择非 mint 操作，而 tokenId state 已经不在 options 中，清空
  React.useEffect(() => {
    if (operation && operation !== 'mint' && operation !== 'branch' && tokenId && !tokenIdOptions.includes(tokenId)) {
      setTokenId('');
    }
  }, [operation, tokenIdOptions, tokenId]);

  // tokenId 变化处理，自动填充 tokenName 和 assetType
  const handleTokenIdChange = (value: string) => {
    setTokenId(value);
    const allElements = elementRegistry.getAll();
    let matched: any = null;
    allElements.forEach((el: any) => {
      const docs = el.businessObject.documentation;
      if (Array.isArray(docs) && docs.length) {
        try {
          const p = JSON.parse(docs[0].text);
          if (p.tokenId === value && p.assetType === assetType) {
            matched = p;
          }
        } catch {
          // ignore
        }
      }
    });
    if (matched) {
      setTokenName(matched.tokenName || '');
      setAssetType(matched.assetType || '');
      setTokenURL(matched.tokenURL || '');
    }
  };

  // 更新到 BPMN
  const updateDataToBPMN = () => {
    if (!shape) return;

    commandStack.execute('element.updateLabel', {
      element: shape,
      newLabel: elementName || shape.businessObject.name,
    });

    const payload: any = { assetType, operation, tokenName };
    if (caller) {
      const pureCaller = caller.split('_ChoreographyTask_')[0];
      payload.caller = pureCaller;
    }
    if ((assetType === 'transferable' && operation === 'Transfer') ||
      (assetType === 'distributive' && ['approve', 'remove approval'].includes(operation))) {
      if (callee.length) {
        payload.callee = callee.map(id => id.split('_ChoreographyTask_')[0]);
      }
    }
    if (assetType === 'transferable') {
      if (tokenType) payload.tokenType = tokenType;
      if (tokenName) payload.tokenName = tokenName;
      if (tokenType === 'FT' && tokenNumber && operation !== 'query') {
        payload.tokenNumber = tokenNumber;
      }
    }
    if (!(assetType === 'transferable' && tokenType === 'FT') && tokenId) {
      payload.tokenId = tokenId;
      if (tokenURL) payload.tokenURL = tokenURL;
    }
    if (assetType === 'value-added' && operation !== 'query' && refTokenIds.length > 0) {
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
    if ((operation === 'mint' || operation === 'branch') && tokenId && tokenId !== originalTokenId && tokenIdOptions.includes(tokenId)) {
      message.warning('The tokenId already exists. Please choose a different one');
      return;
    }
    updateDataToBPMN();
    onClose(true);
  };

  // 显示条件
  const shouldShowCallee = React.useMemo(() => {
    return (
      (assetType === 'transferable' && operation === 'Transfer') ||
      (assetType === 'distributive' && ['approve', 'remove approval'].includes(operation))
    );
  }, [assetType, operation]);

  const shouldShowTokenName = true;
  const shouldShowTokenNumber = React.useMemo(() => {
    return assetType === 'transferable' && tokenType === 'FT' && operation !== 'query';
  }, [assetType, tokenType, operation]);
  const shouldShowTokenId = React.useMemo(() => {
    return !(assetType === 'transferable' && tokenType === 'FT');
  }, [assetType, tokenType]);

  return (
    <Modal
      title={`Edit fixed fields for element ${dataElementId}`}
      open={isModalOpen}
      onOk={handleOk}
      onCancel={() => onClose(false)}
      width={600}
    >
      {/* 1.elementName */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Element Name:</label>
        <Input value={elementName} onChange={e => setElementName(e.target.value)} />
      </div>

      {/* 2.assetType */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Asset Type:</label>
        <Select
          value={assetType}
          onChange={value => {
            setAssetType(value);
            setOperation('');
            setTokenType('');
            setTokenName('');
            setTokenNumber('');
            setCallee([]);
            setTokenId('');
            setRefTokenIds([]);
          }}
          allowClear
          style={{ width: '100%' }}
        >
          <Select.Option value="distributive">Distributive</Select.Option> {/* distributive */}
          <Select.Option value="transferable">Transferable</Select.Option> {/* transferable */}
          <Select.Option value="value-added">Value-added</Select.Option> {/* value-added */}
        </Select>
      </div>

      {/* 3.operation */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Operation:</label>
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

      {/* 4.tokenType */}
      {assetType === 'transferable' && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token Type:</label>
          <Select
            value={tokenType}
            onChange={value => {
              setTokenType(value);
              setTokenName('');
              setTokenNumber('');
              setTokenId('');
              setRefTokenIds([]);
            }}
            allowClear
            style={{ width: '100%' }}
          >
            <Select.Option value="NFT">NFT</Select.Option>
            <Select.Option value="FT">FT</Select.Option>
          </Select>
        </div>
      )}

      {/* 5.tokenId */}
      {shouldShowTokenId && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token ID:</label>
          {(operation === 'mint' || operation === 'branch') ? (
            <Input
              value={tokenId}
              onChange={e => setTokenId(e.target.value)}
              placeholder="Enter new token ID"
            />
          ) : (
            <Select
              value={tokenId}
              onChange={handleTokenIdChange}
              options={tokenIdOptions.map(id => ({ label: id, value: id }))}
              placeholder={
                tokenIdOptions.length > 0 ? 'Select token ID' : 'No available token ID'
              }
              allowClear
              style={{ width: '100%' }}
              disabled={tokenIdOptions.length === 0}
            />
          )}
        </div>
      )}

      {/* 6.tokenName */}
      {shouldShowTokenName && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token Name:</label>

          {assetType === 'transferable' && tokenType === 'FT' && operation !== 'mint' ? (
            // FT 场景（除 mint 之外）保持原下拉选择，可手动选已有名称
            <Select
              value={tokenName}
              onChange={setTokenName}
              options={tokenNameOptions.map(n => ({ label: n, value: n }))}
              placeholder={
                tokenNameOptions.length > 0
                  ? 'Select an existing FT token name'
                  : 'No available token name'
              }
              allowClear
              style={{ width: '100%' }}
              disabled={tokenNameOptions.length === 0}
            />
          ) : (
            // 其它场景：只有 mint 时可输入，否则禁用
            <Input
              value={tokenName}
              onChange={e => setTokenName(e.target.value)}
              placeholder="Enter token name"
              disabled={!(operation === 'mint' || operation === 'branch')}
            />
          )}
        </div>
      )}

      {/*7. tokenURI */}
      {shouldShowTokenId && tokenId && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token URL:</label>
          {operation === 'mint' || operation === 'branch' ? (
            <Input
              value={tokenURL}
              onChange={e => setTokenURL(e.target.value)}
              placeholder="Enter token URL"
            />
          ) : (
            <Input
              value={tokenURL}
              disabled
              placeholder="Auto-filled token URL"
            />
          )}
        </div>
      )}

      {/* 8.tokenNumber */}
      {shouldShowTokenNumber && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token Number:</label>
          <Input value={tokenNumber} onChange={e => setTokenNumber(e.target.value)} />
        </div>
      )}

      {/* caller */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>
          {operationToCallerLabel[operation] || 'Caller'}:
        </label>
        <Select
          value={caller}
          onChange={setCaller}
          options={participantOptions}
          placeholder={`Please select ${operationToCallerLabel[operation] || 'caller'}`}
          allowClear
          style={{ width: '100%' }}
        />
      </div>

      {/* callee */}
      {shouldShowCallee && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>
            {operationToCalleeLabel[operation] || 'Callee'}:
          </label>
          <Select
            mode="multiple"
            value={callee}
            onChange={setCallee}
            options={participantOptions}
            placeholder={`Please select ${operationToCalleeLabel[operation] || 'callee'}`}
            allowClear
            style={{ width: '100%' }}
          />
        </div>
      )}

      {/* Reference Token */}
      {assetType === 'value-added' && operation != 'query' && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Reference Token:</label>
          <Select
            mode="multiple"
            value={refTokenIds}
            onChange={setRefTokenIds}
            options={refTokenIdOptions.map(id => ({ label: id, value: id }))}
            placeholder={refTokenIdOptions.length > 0 ? 'Select reference token(s)' : 'No available token'}
            allowClear
            style={{ width: '100%' }}
          />
        </div>
      )}


    </Modal>
  );
}
