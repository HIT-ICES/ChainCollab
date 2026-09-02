import * as React from 'react';
import { Modal, Input, Select, message, Button, Table } from 'antd';
import {
  ASSET_OPERATION_OPTIONS,
  ASSET_OPERATION_OPTIONS_BY_ASSET_TYPE,
  getAssetData,
  getAssetOperationData,
  getParticipantOptions,
  getPrimaryAssetElement,
  getReceivingParticipantIds,
  updateAssetOperation,
} from '../utils/assetExtension';

interface FixedFieldsModalProps {
  dataElementId: string;
  open: boolean;
  onClose: (saved: boolean) => void;
}

type OutputRow = {
  key: number;
  name: string;
  type: string;
  dataType: string;
};

export default function AssetTaskModal({
  dataElementId,
  open: isModalOpen,
  onClose,
}: FixedFieldsModalProps) {
  const modeler = window.bpmnjs;
  const elementRegistry = modeler.get('elementRegistry');
  const modeling = modeler.get('modeling');
  const moddle = modeler.get('moddle');
  const eventBus = modeler.get('eventBus');
  const shape = elementRegistry.get(dataElementId);

  const [elementName, setElementName] = React.useState('');
  const [operation, setOperation] = React.useState('');
  const [tokenNumber, setTokenNumber] = React.useState('');
  const [outputList, setOutputList] = React.useState<OutputRow[]>([]);
  const [participantOptions, setParticipantOptions] = React.useState<{ value: string; label: string }[]>([]);
  const [participantOptionsKey, setParticipantOptionsKey] = React.useState(0);
  const [primaryAsset, setPrimaryAsset] = React.useState<any>(null);

  const refreshDerivedData = React.useCallback(() => {
    setParticipantOptions(getParticipantOptions(elementRegistry));
    setParticipantOptionsKey(key => key + 1);
    const assetElement = shape ? getPrimaryAssetElement(shape, elementRegistry) : null;
    setPrimaryAsset(assetElement ? getAssetData(assetElement) : null);
  }, [elementRegistry, shape]);

  const loadDataFromBPMN = () => {
    if (!shape) return;

    const data = getAssetOperationData(shape);
    setElementName(shape.businessObject.name || '');
    setOperation(data.operation || '');
    setTokenNumber(data.tokenNumber || '');
    setOutputList(
      Object.keys(data.outputs || {}).map((key, index) => ({
        key: index,
        name: key,
        type: data.outputs[key].type,
        dataType: data.outputs[key].dataType,
      }))
    );
    refreshDerivedData();
  };

  React.useEffect(() => {
    if (!isModalOpen) return;

    setElementName('');
    setOperation('');
    setTokenNumber('');
    setOutputList([]);
    loadDataFromBPMN();

    eventBus.on('commandStack.changed', refreshDerivedData);
    return () => {
      eventBus.off('commandStack.changed', refreshDerivedData);
    };
  }, [shape, isModalOpen, refreshDerivedData]);

  const assetType = primaryAsset?.assetType || '';
  const tokenType = primaryAsset?.tokenType || '';
  const activeOperationOptions = assetType ? ASSET_OPERATION_OPTIONS_BY_ASSET_TYPE[assetType] || [] : ASSET_OPERATION_OPTIONS;
  const receivingParticipants = shape ? getReceivingParticipantIds(shape) : [];

  const getOutputTypes = () => {
    if (assetType === 'transferable' && tokenType === 'FT') {
      return [{ value: 'balance', label: 'Balance', dataType: 'number' }];
    }
    if (assetType === 'transferable' && tokenType === 'NFT') {
      return [
        { value: 'URI', label: 'URI', dataType: 'string' },
        { value: 'owner', label: 'Owner', dataType: 'string' },
      ];
    }
    if (assetType === 'value-added') {
      return [
        { value: 'URI', label: 'URI', dataType: 'string' },
        { value: 'owner', label: 'Owner', dataType: 'string' },
        { value: 'referring', label: 'Referring', dataType: 'string' },
        { value: 'referred', label: 'Referred', dataType: 'string' },
      ];
    }
    if (assetType === 'distributive') {
      return [
        { value: 'isowner', label: 'isOwner', dataType: 'boolean' },
        { value: 'isuser', label: 'isUser', dataType: 'boolean' },
        { value: 'URI', label: 'URI', dataType: 'string' },
      ];
    }
    return [];
  };

  const updateDataToBPMN = () => {
    if (!shape) return;

    modeling.updateLabel(shape, elementName || shape.businessObject.name);

    const existing = getAssetOperationData(shape);
    const outputs = {};
    if (operation === 'query') {
      outputList.forEach(item => {
        if (item.name) {
          outputs[item.name] = {
            type: item.type,
            dataType: item.dataType,
          };
        }
      });
    }

    updateAssetOperation(shape, moddle, modeling, {
      ...existing,
      operation,
      tokenNumber: assetType === 'transferable' && tokenType === 'FT' && operation !== 'query'
        ? tokenNumber
        : '',
      recipientRefs: [],
      outputs,
    });
  };

  const handleOk = () => {
    if (!operation) {
      message.warning('Please select operation');
      return;
    }

    if (assetType && !activeOperationOptions.includes(operation)) {
      message.warning(`Operation ${operation} is not valid for asset type ${assetType}`);
      return;
    }

    if (assetType === 'transferable' && tokenType === 'FT' && operation !== 'query') {
      const raw = (tokenNumber || '').trim();
      if (!raw) {
        message.warning('tokenNumber is required for Transferable FT operations');
        return;
      }
      const num = Number(raw);
      if (!Number.isFinite(num) || num <= 0) {
        message.warning('tokenNumber must be a positive number');
        return;
      }
    }

    const multiCalleeOperations = ['grant usage rights', 'revoke usage rights'];
    const singleCalleeOperations = ['Transfer', 'transfer'];
    const calleeFreeOperations = ['mint', 'burn', 'query', 'branch', 'merge'];

    if (multiCalleeOperations.includes(operation) && receivingParticipants.length === 0) {
      message.warning(`${operation} requires at least one non-initiating participant on the AssetTask`);
      return;
    }

    if (singleCalleeOperations.includes(operation) && receivingParticipants.length !== 1) {
      message.warning(`${operation} requires exactly one non-initiating participant on the AssetTask`);
      return;
    }

    if (calleeFreeOperations.includes(operation) && receivingParticipants.length > 0) {
      message.warning(`${operation} must keep only the Contract placeholder as non-initiating participant`);
      return;
    }

    updateDataToBPMN();
    onClose(true);
  };

  const handleAddOutput = () => {
    const outputTypes = getOutputTypes();
    if (outputTypes.length === 0) {
      message.warning('Please connect/configure an Asset before adding query outputs');
      return;
    }
    const first = outputTypes[0];
    setOutputList([
      ...outputList,
      {
        key: Date.now(),
        name: '',
        type: first.value,
        dataType: first.dataType,
      },
    ]);
  };

  const outputColumns = [
    {
      title: 'Name',
      dataIndex: 'name',
      render: (_: string, record: OutputRow) => (
        <Input
          value={record.name}
          onChange={e => {
            setOutputList(list => list.map(item => item.key === record.key ? { ...item, name: e.target.value } : item));
          }}
        />
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      render: (_: string, record: OutputRow) => (
        <Select
          value={record.type}
          style={{ width: '100%' }}
          onChange={value => {
            const selected = getOutputTypes().find(item => item.value === value);
            setOutputList(list => list.map(item => item.key === record.key
              ? { ...item, type: value, dataType: selected?.dataType || item.dataType }
              : item));
          }}
        >
          {getOutputTypes().map(item => (
            <Select.Option key={item.value} value={item.value}>{item.label}</Select.Option>
          ))}
        </Select>
      ),
    },
    {
      title: 'Data Type',
      dataIndex: 'dataType',
    },
    {
      title: 'Action',
      dataIndex: 'action',
      render: (_: string, record: OutputRow) => (
        <Button danger onClick={() => setOutputList(list => list.filter(item => item.key !== record.key))}>
          Delete
        </Button>
      ),
    },
  ];

  return (
    <Modal
      title={`Edit Asset Operation for ${dataElementId}`}
      open={isModalOpen}
      onOk={handleOk}
      onCancel={() => onClose(false)}
      width={720}
    >
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Element Name:</label>
        <Input value={elementName} onChange={e => setElementName(e.target.value)} />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>Operation:</label>
        <Select
          value={operation}
          disabled
          style={{ width: '100%' }}
        >
          {activeOperationOptions.map(item => (
            <Select.Option key={item} value={item}>{item}</Select.Option>
          ))}
        </Select>
      </div>

      {(operation === 'Transfer' || operation === 'transfer') && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Recipient:</label>
          <Select
            mode="multiple"
            value={receivingParticipants}
            options={participantOptions}
            disabled
            style={{ width: '100%' }}
          />
        </div>
      )}

      {['grant usage rights', 'revoke usage rights'].includes(operation) && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Recipients:</label>
          <Select
            key={participantOptionsKey}
            mode="multiple"
            value={receivingParticipants}
            options={participantOptions}
            disabled
            style={{ width: '100%' }}
          />
        </div>
      )}

      {assetType === 'transferable' && tokenType === 'FT' && operation !== 'query' && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4 }}>Token Number:</label>
          <Input value={tokenNumber} onChange={e => setTokenNumber(e.target.value)} />
        </div>
      )}

      {operation === 'query' && (
        <div style={{ marginBottom: 16 }}>
          <Button onClick={handleAddOutput} style={{ marginBottom: 12 }}>
            Add Output
          </Button>
          <Table
            rowKey="key"
            dataSource={outputList}
            columns={outputColumns}
            pagination={false}
            size="small"
          />
        </div>
      )}
    </Modal>
  );
}
