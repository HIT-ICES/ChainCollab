import * as React from 'react';
import { Modal, Input, Select, message, Checkbox } from 'antd';
import { getAssetData, getDerivedRefTokenIds, isAssetElement } from '../utils/assetExtension';

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
  const modeling = modeler.get('modeling');
  const eventBus = modeler.get('eventBus');
  const shape = elementRegistry.get(dataElementId);

  const [elementName, setElementName] = React.useState('');
  const [assetType, setAssetType] = React.useState('');
  const [tokenType, setTokenType] = React.useState('');
  const [tokenName, setTokenName] = React.useState('');
  const [tokenId, setTokenId] = React.useState('');
  const [tokenURL, setTokenURL] = React.useState('');
  const [tokenHasExistInERC, setTokenHasExistInERC] = React.useState(false);
  const [derivedRefTokenIds, setDerivedRefTokenIds] = React.useState<string[]>([]);

  const loadDataFromBPMN = () => {
    if (!shape) return;

    const data = getAssetData(shape);
    setElementName(shape.businessObject.name || '');
    setAssetType(data.assetType || '');
    setTokenType(data.tokenType || '');
    setTokenName(data.tokenName || '');
    setTokenId(data.tokenId || '');
    setTokenURL(data.tokenURL || '');
    setTokenHasExistInERC(Boolean(data.tokenHasExistInERC));
    setDerivedRefTokenIds(getDerivedRefTokenIds(shape, elementRegistry));
  };

  React.useEffect(() => {
    if (isModalOpen) {
      setElementName('');
      setAssetType('');
      setTokenType('');
      setTokenName('');
      setTokenId('');
      setTokenURL('');
      setTokenHasExistInERC(false);
      setDerivedRefTokenIds([]);
      loadDataFromBPMN();
    }
  }, [shape, isModalOpen]);

  React.useEffect(() => {
    if (!isModalOpen || !shape) return;

    const refreshDerivedRefs = () => {
      setDerivedRefTokenIds(getDerivedRefTokenIds(shape, elementRegistry));
    };

    eventBus.on('commandStack.changed', refreshDerivedRefs);
    return () => {
      eventBus.off('commandStack.changed', refreshDerivedRefs);
    };
  }, [eventBus, elementRegistry, shape, isModalOpen]);

  const updateDataToBPMN = () => {
    if (!shape) return;

    modeling.updateLabel(shape, elementName || shape.businessObject.name);

    const properties: any = {
      assetType,
      tokenType: assetType === 'transferable' ? tokenType : undefined,
      tokenName,
      tokenId: assetType === 'transferable' && tokenType === 'FT' ? undefined : tokenId,
      tokenURL: assetType === 'distributive' ? tokenURL : undefined,
      tokenHasExistInERC: assetType === 'transferable' && tokenType === 'FT'
        ? undefined
        : tokenHasExistInERC,
      documentation: undefined,
    };

    modeling.updateProperties(shape, properties);
  };

  const handleOk = () => {
    if (!assetType) {
      message.warning('Please select asset type');
      return;
    }

    if (assetType === 'transferable' && !tokenType) {
      message.warning('Please select token type');
      return;
    }

    const name = (tokenName || '').trim();
    if (!name) {
      message.warning('tokenName is required');
      return;
    }

    if (!(assetType === 'transferable' && tokenType === 'FT') && !(tokenId || '').trim()) {
      message.warning('tokenId is required');
      return;
    }

    if (assetType === 'transferable' && tokenType === 'FT') {
      const duplicated = elementRegistry.getAll().some((el: any) => {
        if (el.id === dataElementId || !isAssetElement(el)) return false;
        const data = getAssetData(el);
        return data.assetType === 'transferable' &&
          data.tokenType === 'FT' &&
          (data.tokenName || '').trim() === name;
      });

      if (duplicated) {
        message.warning('FT tokenName already exists. Please choose a different tokenName');
        return;
      }
    }

    if (tokenId) {
      const duplicated = elementRegistry.getAll().some((el: any) => {
        if (el.id === dataElementId || !isAssetElement(el)) return false;
        return getAssetData(el).tokenId === tokenId;
      });

      if (duplicated) {
        message.warning('The tokenId already exists. Please choose a different one');
        return;
      }
    }

    updateDataToBPMN();
    onClose(true);
  };

  const shouldShowTokenId = !(assetType === 'transferable' && tokenType === 'FT');

  return (
    <Modal
      title={`Edit Asset Definition for ${dataElementId}`}
      open={isModalOpen}
      onOk={handleOk}
      onCancel={() => onClose(false)}
      width={600}
    >
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Element Name:</label>
        <Input value={elementName} onChange={e => setElementName(e.target.value)} />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Asset Type:</label>
        <Select
          value={assetType}
          onChange={value => {
            setAssetType(value);
            setTokenType('');
            setTokenName('');
            setTokenId('');
            setTokenURL('');
            setTokenHasExistInERC(false);
          }}
          allowClear
          style={{ width: '100%' }}
        >
          <Select.Option value="distributive">Distributive</Select.Option>
          <Select.Option value="transferable">Transferable</Select.Option>
          <Select.Option value="value-added">Value-added</Select.Option>
        </Select>
      </div>

      {assetType === 'transferable' && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token Type:</label>
          <Select
            value={tokenType}
            onChange={value => {
              setTokenType(value);
              setTokenId('');
              setTokenHasExistInERC(false);
            }}
            allowClear
            style={{ width: '100%' }}
          >
            <Select.Option value="NFT">NFT</Select.Option>
            <Select.Option value="FT">FT</Select.Option>
          </Select>
        </div>
      )}

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
              Token already exists in ERC contract
            </Checkbox>
          </div>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Token Name:</label>
        <Input
          value={tokenName}
          onChange={e => setTokenName(e.target.value)}
          placeholder="Enter token name"
        />
      </div>

      {assetType === 'distributive' && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token URL:</label>
          <Input
            value={tokenURL}
            onChange={e => setTokenURL(e.target.value)}
            placeholder="Enter token URL"
          />
        </div>
      )}

      {assetType === 'value-added' && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Reference Token IDs:</label>
          <Select
            mode="multiple"
            value={derivedRefTokenIds}
            disabled
            style={{ width: '100%' }}
            placeholder="Derived from branch/merge AssetTask inputs"
          />
        </div>
      )}
    </Modal>
  );
}
