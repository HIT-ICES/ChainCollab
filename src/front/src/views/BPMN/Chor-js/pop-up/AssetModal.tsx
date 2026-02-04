import * as React from 'react';
import { Modal, Input, Select, message, Checkbox } from 'antd';
import { debounce } from 'lodash';

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
  const [tokenHasExistInERC, setTokenHasExistInERC] = React.useState(false);

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
        setTokenHasExistInERC(parsed.tokenHasExistInERC || false);
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
      setTokenHasExistInERC(false);
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

  // ===== 扫描 tokenId（只读扫描，不执行清理操作）=====
  const scanTokenIds = React.useCallback(() => {
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
  }, [elementRegistry]);

  // 合并扫描逻辑
  const scanAll = React.useCallback(() => {
    scanTokenIds();
    scanFTTokenNames();
  }, [scanTokenIds, scanFTTokenNames]);

  // 防抖版本的扫描函数
  const debouncedScanAll = React.useMemo(
    () => debounce(scanAll, 150),
    [scanAll]
  );

  // 清理防抖函数
  React.useEffect(() => {
    return () => {
      debouncedScanAll.cancel();
    };
  }, [debouncedScanAll]);

  React.useEffect(() => {
    // 初次扫描（立即执行）
    scanAll();
    // 监听模型变化，使用防抖重新扫描
    const handler = () => debouncedScanAll();
    eventBus.on('commandStack.changed', handler);
    return () => {
      eventBus.off('commandStack.changed', handler);
    };
  }, [eventBus, scanAll, debouncedScanAll]);

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
      // 添加 tokenHasExistInERC 字段
      payload.tokenHasExistInERC = tokenHasExistInERC;
    }

    // value-added 的 refTokenIds 由 DataAssociationBehavior 自动管理
    // 但我们必须保存当前状态到 BPMN 文档，以便文件重新加载后保持数据
    // 即使是空数组也要保存，这样可以清除旧的引用
    if (assetType === 'value-added') {
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

    // 如果 tokenId 发生了变化，触发全局同步
    if (tokenId && tokenId !== originalTokenId) {
      syncRefTokenIdsGlobally(originalTokenId, tokenId);
    }
  };

  // 全局同步 refTokenIds：将所有引用 oldTokenId 的 DataObject 更新为 newTokenId
  const syncRefTokenIdsGlobally = (oldTokenId: string, newTokenId: string) => {
    if (!oldTokenId || !newTokenId || oldTokenId === newTokenId) return;

    const allElements = elementRegistry.getAll();

    allElements.forEach((el: any) => {
      // 只处理 DataObjectReference
      if (el.type !== 'bpmn:DataObjectReference') return;

      const docs = el.businessObject.documentation;
      if (Array.isArray(docs) && docs.length) {
        try {
          const parsed = JSON.parse(docs[0].text);

          // 检查是否有 refTokenIds 并且包含 oldTokenId
          if (parsed.assetType === 'value-added' && Array.isArray(parsed.refTokenIds)) {
            const index = parsed.refTokenIds.indexOf(oldTokenId);
            if (index !== -1) {
              // 替换 oldTokenId 为 newTokenId
              parsed.refTokenIds[index] = newTokenId;

              // 更新 DataObject
              commandStack.execute('element.updateProperties', {
                element: el,
                properties: {
                  documentation: [
                    modeler._moddle.create('bpmn:Documentation', {
                      text: JSON.stringify(parsed, null, 2),
                    }),
                  ],
                },
              });
            }
          }
        } catch {
          // ignore parse error
        }
      }
    });
  };

  const handleOk = () => {
    // ===== FT tokenName 唯一性校验（DataObject 为 transferable + FT 时）=====
if (assetType === 'transferable' && tokenType === 'FT') {
  const name = (tokenName || '').trim();
  if (name) {
    const allElements = elementRegistry.getAll();
    let duplicated = false;

    allElements.forEach((el: any) => {
      // 跳过当前编辑的元素
      if (el.id === dataElementId) return;
      if (el.type !== 'bpmn:DataObjectReference') return;

      const docs = el.businessObject.documentation;
      if (Array.isArray(docs) && docs.length) {
        try {
          const parsed = JSON.parse(docs[0].text);
          const otherName = (parsed.tokenName || '').trim();
          if (
            parsed.assetType === 'transferable' &&
            parsed.tokenType === 'FT' &&
            otherName &&
            otherName === name
          ) {
            duplicated = true;
          }
        } catch {
          // ignore
        }
      }
    });

    if (duplicated) {
      message.warning('FT tokenName already exists. Please choose a different tokenName');
      return;
    }
  }
}

    // 验证 tokenId 是否重复 - 实时扫描所有 DataObject
    if (tokenId) {
      const allElements = elementRegistry.getAll();
      const existingTokenIds = new Set<string>();

      allElements.forEach((el: any) => {
        // 跳过当前编辑的元素
        if (el.id === dataElementId) return;

        const docs = el.businessObject.documentation;
        if (Array.isArray(docs) && docs.length) {
          try {
            const parsed = JSON.parse(docs[0].text);
            if (el.type === 'bpmn:DataObjectReference' && parsed.tokenId) {
              existingTokenIds.add(parsed.tokenId);
            }
          } catch {
            // ignore
          }
        }
      });

      if (existingTokenIds.has(tokenId)) {
        message.warning('The tokenId already exists. Please choose a different one');
        return;
      }
    }
    updateDataToBPMN();
    onClose(true);
  };

  // 检查 DataObject 是否被 branch/merge Task 使用（输出连接）
  const isUsedByBranchMergeTask = React.useMemo(() => {
    if (!shape || assetType !== 'value-added') return false;

    const incoming = shape.incoming || [];

    // 查找 DataOutputAssociation 连线（Task -> DataObject）
    for (const connection of incoming) {
      const connBo = connection.businessObject;
      if (connBo.$type === 'bpmn:DataOutputAssociation') {
        const taskElement = connection.source;

        // 检查 Task 的 operation
        if (taskElement && taskElement.type === 'bpmn:Task') {
          const docs = taskElement.businessObject.documentation;
          if (Array.isArray(docs) && docs.length) {
            try {
              const parsed = JSON.parse(docs[0].text);
              if (parsed.operation && ['branch', 'merge'].includes(parsed.operation)) {
                return true;
              }
            } catch {
              // ignore
            }
          }
        }
      }
    }
    return false;
  }, [shape, assetType]);

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
          <div style={{ marginTop: 8 }}>
            <Checkbox
              checked={tokenHasExistInERC}
              onChange={e => setTokenHasExistInERC(e.target.checked)}
            >
              Token already exists in ERC contract (skip mint operation)
            </Checkbox>
          </div>
          {tokenHasExistInERC && (
            <div style={{ fontSize: 12, color: '#1890ff', marginTop: 4, paddingLeft: 24 }}>
              ℹ️ This token will be treated as already minted. A default mint owner will be assigned based on participant bindings.
            </div>
          )}
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
            mode="multiple"
            value={refTokenIds}
            disabled
            style={{ width: '100%' }}
            placeholder="Auto-filled from Task connections"
          />
          <div style={{ fontSize: 12, color: '#1890ff', marginTop: 4, padding: '4px 8px', background: '#e6f7ff', border: '1px solid #91d5ff', borderRadius: 4 }}>
            {isUsedByBranchMergeTask ? (
              <>ℹ️ This DataObject is created by a branch/merge Task. Reference Token IDs are automatically collected from DataObjects connected to that Task.</>
            ) : (
              <>ℹ️ For value-added assets, Reference Token IDs are automatically managed through Task connections. Connect this DataObject as output of a branch/merge Task to populate refTokenIds.</>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
