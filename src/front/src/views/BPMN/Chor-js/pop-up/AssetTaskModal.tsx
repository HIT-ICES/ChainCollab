import * as React from 'react';
import { Modal, Input, Select, message, Button, Table } from 'antd';

interface FixedFieldsModalProps {
  dataElementId: string;
  open: boolean;
  onClose: (saved: boolean) => void;
}

export default function AssetTaskModal({
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
  const [tokenHasExistInERC, setTokenHasExistInERC] = React.useState(false);
  // 新增：tokenId 和 FT tokenName 可选列表
  const [tokenIdOptions, setTokenIdOptions] = React.useState<string[]>([]);
  const [tokenNameOptions, setTokenNameOptions] = React.useState<string[]>([]);
  //增值型valueadd - 从 DataObject 读取
  const [refTokenIds, setRefTokenIds] = React.useState<string[]>([]);
  const [outputList, setOutputList] = React.useState([]);
  const operationOptions: Record<string, string[]> = {
    'distributive': ['mint', 'burn', 'grant usage rights', 'revoke usage rights', 'transfer', 'query'],
    'transferable': ['mint', 'burn', 'Transfer', 'query'],
    'value-added': ['branch', 'merge', 'Transfer', 'query'],
  };

  const operationToCallerLabel: Record<string, string> = {
    mint: 'Issuer',              // 发行人
    burn: 'Burner',              // 销毁人
    'grant usage rithts': 'Approver',         // 授权者
    'revoke usage rights': 'Revoker',// 被取消授权者
    query: 'Querier',            // 查询者
    Transfer: 'Sender',          // 转移者
    branch: 'Brancher',          // 分支者
    merge: 'Merger',             // 合并者
  };

  const operationToCalleeLabel: Record<string, string> = {
    mint: 'Receiver',               // 接受者
    burn: 'Burn Target',            // 目标销毁方
    'grant usage rithts': 'Grantee',             // 被授权者
    'revoke usage rights': 'Revoked',   // 被取消授权者
    Transfer: 'Recipient',          // 被转移者
  };


  // 动态决定输出字段类型
  const getOutputTypes = () => {

    // FT（同质化代币）查询
    if (assetType === "transferable" && tokenType === "FT") {
      return [
        { value: "balance", label: "Balance", dataType: "number" },
      ];
    }

    // NFT 转让型
    if (assetType === "transferable" && tokenType === "NFT") {
      return [
        { value: "URI", label: "URI", dataType: "string" },
        { value: "owner", label: "Owner", dataType: "string" },
      ];
    }

    // 增值型（value-added）
    if (assetType === "value-added") {
      return [
         { value: "URI", label: "URI", dataType: "string" },
        { value: "owner", label: "Owner", dataType: "string" },
        { value: "referring", label: "Referring", dataType: "string" },
        { value: "referred", label: "referred", dataType: "string" },
      ];
    }

    // 分发型 distributive
    if (assetType === "distributive") {
      return [
        { value: "isowner", label: "isOwner", dataType: "boolean" },
        { value: "isuser", label: "isUser", dataType: "boolean" },
        { value: "URI", label: "URI", dataType: "string" }
      ];
    }

    return [];
  };

  // 获取连线的 DataObject 的资产信息
  const getLinkedDataObjectAsset = () => {
    if (!shape) return null;

    const incoming = shape.incoming || [];
    const outgoing = shape.outgoing || [];
    const allConnections = [...incoming, ...outgoing];

    // 查找 DataOutputAssociation 连线（Task -> DataObject，主输出）
    for (const connection of allConnections) {
      const connBo = connection.businessObject;
      if (connBo.$type === 'bpmn:DataOutputAssociation') {
        // Task -> DataObject
        const dataObjectElement = connection.target;

        // 检查是否是 DataObjectReference
        if (dataObjectElement && dataObjectElement.type === 'bpmn:DataObjectReference') {
          const docs = dataObjectElement.businessObject.documentation;
          if (Array.isArray(docs) && docs.length) {
            try {
              const parsed = JSON.parse(docs[0].text);
              return parsed;
            } catch {
              // ignore
            }
          }
        }
      }
    }

    // 如果没有输出连接，尝试从输入连接获取（向后兼容）
    for (const connection of allConnections) {
      const connBo = connection.businessObject;
      if (connBo.$type === 'bpmn:DataInputAssociation') {
        // DataObject -> Task
        const dataObjectElement = connection.source;

        // 检查是否是 DataObjectReference
        if (dataObjectElement && dataObjectElement.type === 'bpmn:DataObjectReference') {
          const docs = dataObjectElement.businessObject.documentation;
          if (Array.isArray(docs) && docs.length) {
            try {
              const parsed = JSON.parse(docs[0].text);
              return parsed;
            } catch {
              // ignore
            }
          }
        }
      }
    }
    return null;
  };

  // 获取所有输入 DataObject 的 tokenId（用于 value-added 的 refTokenIds）
  const getIncomingDataObjectTokenIds = () => {
    if (!shape) return [];

    const incoming = shape.incoming || [];
    const tokenIds: string[] = [];

    // 查找所有 DataInputAssociation 连线（DataObject -> Task，引用输入）
    for (const connection of incoming) {
      const connBo = connection.businessObject;
      if (connBo.$type === 'bpmn:DataInputAssociation') {
        const dataObjectElement = connection.source;

        // 检查是否是 DataObjectReference
        if (dataObjectElement && dataObjectElement.type === 'bpmn:DataObjectReference') {
          const docs = dataObjectElement.businessObject.documentation;
          if (Array.isArray(docs) && docs.length) {
            try {
              const parsed = JSON.parse(docs[0].text);
              if (parsed.tokenId) {
                tokenIds.push(parsed.tokenId);
              }
            } catch {
              // ignore
            }
          }
        }
      }
    }
    return tokenIds;
  };

  // 从 BPMN 文档加载已有值
  const loadDataFromBPMN = () => {
    if (!shape) return;
    setElementName(shape.businessObject.name || '');

    // 先尝试从连线的 DataObject 获取资产信息
    const linkedAsset = getLinkedDataObjectAsset();

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

        // 如果有连线的 DataObject，优先使用其资产信息
        if (linkedAsset) {
          setAssetType(linkedAsset.assetType || '');
          setTokenType(linkedAsset.tokenType || '');
          setTokenName(linkedAsset.tokenName || '');
          setTokenId(linkedAsset.tokenId || '');
          setOriginalTokenId(linkedAsset.tokenId || '');
          setTokenHasExistInERC(linkedAsset.tokenHasExistInERC || false);

          // 对于 value-added 的 branch/merge 操作，自动从输入连接收集 refTokenIds
          if (linkedAsset.assetType === 'value-added' && parsed.operation && ['branch', 'merge'].includes(parsed.operation)) {
            const incomingTokenIds = getIncomingDataObjectTokenIds();
            setRefTokenIds(incomingTokenIds);
          } else if (linkedAsset.assetType === 'value-added' && Array.isArray(linkedAsset.refTokenIds)) {
            // 否则从 DataObject 读取（向后兼容）
            setRefTokenIds(linkedAsset.refTokenIds);
          } else {
            setRefTokenIds([]);
          }
        } else {
          // 否则使用 Task 自己保存的资产信息（向后兼容旧数据）
          setAssetType(parsed.assetType || '');
          setTokenType(parsed.tokenType || '');
          setTokenName(parsed.tokenName || '');
          const loadedTokenId = parsed.tokenId || '';
          setTokenId(loadedTokenId);
          setOriginalTokenId(loadedTokenId);
          // 向后兼容：从 Task 读取 refTokenIds
          if (parsed.assetType === 'value-added' && Array.isArray(parsed.refTokenIds)) {
            setRefTokenIds(parsed.refTokenIds);
          } else {
            setRefTokenIds([]);
          }
        }

        setOperation(parsed.operation || '');
        setTokenNumber(parsed.tokenNumber || '');
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
        if (parsed.outputs) {
          const list = Object.keys(parsed.outputs).map((key, index) => ({
            key: index,
            name: key,
            type: parsed.outputs[key].type,
            dataType: parsed.outputs[key].dataType,
          }));
          setOutputList(list);
        } else {
          setOutputList([]);
        }
      } catch {
        // ignore parse error
      }
    } else if (linkedAsset) {
      // 如果 Task 没有 documentation 但有连线的 DataObject
      setAssetType(linkedAsset.assetType || '');
      setTokenType(linkedAsset.tokenType || '');
      setTokenName(linkedAsset.tokenName || '');
      setTokenId(linkedAsset.tokenId || '');
      setOriginalTokenId(linkedAsset.tokenId || '');
      setTokenHasExistInERC(linkedAsset.tokenHasExistInERC || false);
      // refTokenIds 也从 DataObject 读取
      if (linkedAsset.assetType === 'value-added' && Array.isArray(linkedAsset.refTokenIds)) {
        setRefTokenIds(linkedAsset.refTokenIds);
      } else {
        setRefTokenIds([]);
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

  // 监听连接变化，自动同步 refTokenIds 到输出 DataObject
  React.useEffect(() => {
    if (!isModalOpen || !shape) return;

    const handleConnectionChange = () => {
      // 只在 value-added 的 branch/merge 操作时才需要同步
      const linkedAsset = getLinkedDataObjectAsset();
      if (!linkedAsset || linkedAsset.assetType !== 'value-added') return;

      const doc = shape.businessObject.documentation;
      if (!Array.isArray(doc) || !doc.length) return;

      try {
        const parsed = JSON.parse(doc[0].text);
        if (!parsed.operation || !['branch', 'merge'].includes(parsed.operation)) return;

        // 收集最新的输入 tokenIds
        const incomingTokenIds = getIncomingDataObjectTokenIds();

        // 更新 refTokenIds 状态
        setRefTokenIds(incomingTokenIds);

        // 直接更新输出 DataObject 的 refTokenIds
        const outgoing = shape.outgoing || [];
        for (const connection of outgoing) {
          const connBo = connection.businessObject;
          if (connBo.$type === 'bpmn:DataOutputAssociation') {
            const dataObjectElement = connection.target;

            if (dataObjectElement && dataObjectElement.type === 'bpmn:DataObjectReference') {
              const docs = dataObjectElement.businessObject.documentation;
              if (Array.isArray(docs) && docs.length) {
                try {
                  const parsed = JSON.parse(docs[0].text);
                  parsed.refTokenIds = incomingTokenIds;

                  commandStack.execute('element.updateProperties', {
                    element: dataObjectElement,
                    properties: {
                      documentation: [
                        modeler._moddle.create('bpmn:Documentation', {
                          text: JSON.stringify(parsed, null, 2),
                        }),
                      ],
                    },
                  });
                } catch {
                  // ignore
                }
              }
            }
          }
        }
      } catch {
        // ignore
      }
    };

    // 监听连接创建和删除事件
    eventBus.on('connection.added', handleConnectionChange);
    eventBus.on('connection.removed', handleConnectionChange);
    eventBus.on('commandStack.changed', handleConnectionChange);

    return () => {
      eventBus.off('connection.added', handleConnectionChange);
      eventBus.off('connection.removed', handleConnectionChange);
      eventBus.off('commandStack.changed', handleConnectionChange);
    };
  }, [isModalOpen, shape, eventBus, commandStack, modeler]);

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
          if ((parsed.operation === 'mint' || parsed.operation === 'branch' || parsed.operation === 'merge') && parsed.tokenId) {
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

    // 对所有非 mint 等操作且 tokenId 不在新列表中的元素，清理 tokenId
    allElements.forEach((el: any) => {
      const docs = el.businessObject.documentation;
      if (Array.isArray(docs) && docs.length) {
        try {
          const parsed = JSON.parse(docs[0].text);
          if (parsed.tokenId && (parsed.operation === 'mint' || parsed.operation === 'branch' || parsed.operation === 'merge') && !newTokenIdsSet.has(parsed.tokenId)) {
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

  // tokenId 现在从 DataObject 读取，不需要验证和清空逻辑
  // React.useEffect(() => {
  //   if (operation && operation !== 'mint' && operation !== 'branch' && operation !== 'merge' && tokenId && !tokenIdOptions.includes(tokenId)) {
  //     setTokenId('');
  //   }
  // }, [operation, tokenIdOptions, tokenId]);

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

  // 更新到 BPMN - 只保存操作相关信息，不保存资产信息
  const updateDataToBPMN = () => {
    if (!shape) return;

    commandStack.execute('element.updateLabel', {
      element: shape,
      newLabel: elementName || shape.businessObject.name,
    });

    const payload: any = { operation };

    if (caller) {
      const pureCaller = caller.split('_ChoreographyTask_')[0];
      payload.caller = pureCaller;
    }

    if ((assetType === 'transferable' && operation === 'Transfer') ||
      (assetType === 'value-added' && operation === 'Transfer') ||
      (assetType === 'distributive' && ['grant usage rights', 'revoke usage rights', 'transfer'].includes(operation))) {
      if (callee.length) {
        payload.callee = callee.map(id => id.split('_ChoreographyTask_')[0]);
      }
    }

    if (assetType === 'transferable' && tokenType === 'FT' && tokenNumber && operation !== 'query') {
      payload.tokenNumber = tokenNumber;
    }

    // 对于 value-added 的 branch/merge 操作，将 refTokenIds 更新到输出的 DataObject
    if (assetType === 'value-added' && operation && ['branch', 'merge'].includes(operation)) {
      updateOutputDataObjectRefTokenIds();
    }

    // Only query operation supports outputs
    if (operation === "query") {
      const outputs = {};
      outputList.forEach(item => {
        outputs[item.name] = {
          type: item.type,
          dataType: item.dataType,
        };
      });
      payload.outputs = outputs;
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

  // 更新输出 DataObject 的 refTokenIds
  const updateOutputDataObjectRefTokenIds = () => {
    if (!shape) return;

    const outgoing = shape.outgoing || [];

    // 查找 DataOutputAssociation 连线（Task -> DataObject）
    for (const connection of outgoing) {
      const connBo = connection.businessObject;
      if (connBo.$type === 'bpmn:DataOutputAssociation') {
        const dataObjectElement = connection.target;

        // 检查是否是 DataObjectReference
        if (dataObjectElement && dataObjectElement.type === 'bpmn:DataObjectReference') {
          const docs = dataObjectElement.businessObject.documentation;
          if (Array.isArray(docs) && docs.length) {
            try {
              const parsed = JSON.parse(docs[0].text);

              // 更新 refTokenIds
              parsed.refTokenIds = refTokenIds;

              // 保存回 DataObject
              commandStack.execute('element.updateProperties', {
                element: dataObjectElement,
                properties: {
                  documentation: [
                    modeler._moddle.create('bpmn:Documentation', {
                      text: JSON.stringify(parsed, null, 2),
                    }),
                  ],
                },
              });
            } catch {
              // ignore
            }
          }
        }
      }
    }
  };

  const handleOk = () => {
    // 检查是否连接了 DataObject
    const linkedAsset = getLinkedDataObjectAsset();
    if (!linkedAsset) {
      message.warning('Please connect this Task to a DataObject first to define the asset');
      return;
    }

    if (shouldShowCallee && (!callee || callee.length === 0)) {
      message.warning(
        `Please select ${operationToCalleeLabel[operation] || 'callee'}`
      );
      return;
    }
    updateDataToBPMN();
    onClose(true);
  };

  // 显示条件
  const shouldShowCallee = React.useMemo(() => {
    return (
      (assetType === 'transferable' && operation === 'Transfer') ||
      (assetType === 'value-added' && operation === 'Transfer') ||
      (assetType === 'distributive' && ['grant usage rights', 'revoke usage rights', 'transfer'].includes(operation))
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
      title={`Edit Task behavior for ${dataElementId}`}
      open={isModalOpen}
      onOk={handleOk}
      onCancel={() => onClose(false)}
      width={600}
    >
      {/* 提示：资产信息来自连线的 DataObject */}
      {assetType && (
        <div style={{ marginBottom: 16, padding: 12, background: '#e6f7ff', borderRadius: 4 }}>
          <div style={{ color: '#1890ff', marginBottom: 4 }}>
            📌 Asset information is loaded from the connected DataObject
          </div>
          <div style={{ fontSize: 12, color: '#595959' }}>
            To modify asset properties, please edit the connected DataObject element
          </div>
        </div>
      )}

      {/* 1.elementName */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Element Name:</label>
        <Input value={elementName} onChange={e => setElementName(e.target.value)} />
      </div>

      {/* 2.assetType (只读) */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Asset Type (from DataObject):</label>
        <Select
          value={assetType}
          disabled
          style={{ width: '100%' }}
        >
          <Select.Option value="distributive">Distributive</Select.Option>
          <Select.Option value="transferable">Transferable</Select.Option>
          <Select.Option value="value-added">Value-added</Select.Option>
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

      {/* 4.tokenType (只读) */}
      {assetType === 'transferable' && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token Type (from DataObject):</label>
          <Select
            value={tokenType}
            disabled
            style={{ width: '100%' }}
          >
            <Select.Option value="NFT">NFT</Select.Option>
            <Select.Option value="FT">FT</Select.Option>
          </Select>
        </div>
      )}

      {/* 5.tokenId (只读) */}
      {shouldShowTokenId && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token ID (from DataObject):</label>
          <Input
            value={tokenId}
            disabled
            placeholder="Token ID from connected DataObject"
          />
          {tokenHasExistInERC && (
            <div style={{ fontSize: 12, color: '#52c41a', marginTop: 4, padding: '4px 8px', background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 4 }}>
              ✓ This token is marked as already existing in ERC contract. Validation will assume it has been minted.
            </div>
          )}
        </div>
      )}

      {/* 6.tokenName (只读) */}
      {(
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token Name (from DataObject):</label>
          <Input
            value={tokenName}
            disabled
            placeholder="Token name from connected DataObject"
          />
        </div>
      )}

      {/*7. tokenURI */}
      {/*  {shouldShowTokenId && tokenId && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token URL:</label>
          {operation === 'mint' || operation === 'branch'||operation==='merge' ? (
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
      )} */}

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

      {/* Reference Token IDs (只读，从 DataObject 读取) */}
      {assetType === 'value-added' && refTokenIds.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Reference Token IDs (from DataObject):</label>
          <Select
            mode="multiple"
            value={refTokenIds}
            disabled
            style={{ width: '100%' }}
            placeholder="Reference token IDs from connected DataObject"
          />
          <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
            To modify reference token IDs, please edit the connected DataObject element
          </div>
        </div>
      )}
      {operation === "query" && (
        <div style={{ marginBottom: 20 }}>
          <label style={{ display: "block", marginBottom: 4 }}>Output Fields:</label>

          {/* 无数据不显示表格 */}
          {outputList.length > 0 ? (
            <Table
              dataSource={outputList}
              pagination={false}
              rowKey="key"
              columns={[
                {
                  title: "Type",
                  dataIndex: "type",
                  render: (_, record) => (
                    <Select
                      value={record.type}
                      style={{ width: 140 }}
                      onChange={(v) => {
                        const copy = [...outputList];
                        const t = getOutputTypes().find(o => o.value === v);
                        copy[record.key].type = v;
                        copy[record.key].dataType = t?.dataType || "string";
                        setOutputList(copy);
                      }}
                    >
                      {getOutputTypes().map(o => (
                        <Select.Option key={o.value} value={o.value}>
                          {o.label}
                        </Select.Option>
                      ))}
                    </Select>
                  )
                },

                {
                  title: "Name",
                  dataIndex: "name",
                  render: (_, record) => (
                    <Input
                      value={record.name}
                      onChange={(e) => {
                        const copy = [...outputList];
                        copy[record.key].name = e.target.value;
                        setOutputList(copy);
                      }}
                    />
                  )
                },

                {
                  title: "DataType",
                  dataIndex: "dataType",
                  render: (_, record) => (
                    <Input
                      disabled
                      value={record.dataType}
                      style={{ width: 120 }}
                    />
                  )
                },

                {
                  title: "Action",
                  render: (_, record) => (
                    <a
                      onClick={() => {
                        const kept = outputList.filter(x => x.key !== record.key);
                        setOutputList(kept.map((x, i) => ({ ...x, key: i })));
                      }}
                    >
                      Delete
                    </a>
                  )
                }
              ]}
            />
          ) : (
            <div style={{ margin: "8px 0 12px 0", color: "#999" }}>
              No output fields. Click "Add" to create one.
            </div>
          )}

          {/* Add 按钮 */}
          <Button
            type="primary"
            style={{ marginTop: 10 }}
            onClick={() => {
              const opts = getOutputTypes();
              const copy = [...outputList];
              copy.push({
                key: copy.length,
                name: "",
                type: opts[0]?.value || "",
                dataType: opts[0]?.dataType || "string",
              });
              setOutputList(copy);
            }}
          >
            Add
          </Button>
        </div>
      )}




    </Modal>
  );
}
