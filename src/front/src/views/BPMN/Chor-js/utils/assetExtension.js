export const ASSET_TYPE = 'abc:Asset';
export const ASSET_OPERATION_TYPE = 'abc:AssetOperation';
export const CONTRACT_PARTICIPANT_ID = 'Participant_Contract';
export const CONTRACT_PARTICIPANT_NAME = 'Contract';

const REF_SEPARATOR = ' ';

export const ASSET_KIND_OPTIONS = [
  {
    key: 'transferable-nft',
    label: 'Transferable NFT',
    assetType: 'transferable',
    tokenType: 'NFT'
  },
  {
    key: 'transferable-ft',
    label: 'Transferable FT',
    assetType: 'transferable',
    tokenType: 'FT'
  },
  {
    key: 'distributive',
    label: 'Distributive',
    assetType: 'distributive',
    tokenType: ''
  },
  {
    key: 'value-added',
    label: 'Value-added',
    assetType: 'value-added',
    tokenType: ''
  }
];

export const ASSET_CATEGORY_OPTIONS = [
  {
    key: 'transferable',
    label: 'Transferable',
    assetType: 'transferable'
  },
  {
    key: 'distributive',
    label: 'Distributive',
    assetType: 'distributive'
  },
  {
    key: 'value-added',
    label: 'Value-added',
    assetType: 'value-added'
  }
];

export const TRANSFERABLE_TOKEN_TYPE_OPTIONS = [
  {
    key: 'nft',
    label: 'NFT',
    tokenType: 'NFT'
  },
  {
    key: 'ft',
    label: 'FT',
    tokenType: 'FT'
  }
];

export const ASSET_OPERATION_OPTIONS_BY_ASSET_TYPE = {
  distributive: ['mint', 'burn', 'grant usage rights', 'revoke usage rights', 'transfer', 'query'],
  transferable: ['mint', 'burn', 'Transfer', 'query'],
  'value-added': ['branch', 'merge', 'Transfer', 'burn', 'query']
};

export const ASSET_OPERATION_OPTIONS = Array.from(new Set(
  Object.values(ASSET_OPERATION_OPTIONS_BY_ASSET_TYPE).flat()
));

export function getAssetOperationOptions(assetData) {
  const assetType = assetData?.assetType || '';
  return assetType
    ? ASSET_OPERATION_OPTIONS_BY_ASSET_TYPE[assetType] || []
    : ASSET_OPERATION_OPTIONS;
}

export function isAssetElement(element) {
  return element?.type === ASSET_TYPE || element?.businessObject?.$type === ASSET_TYPE;
}

export function isContractParticipant(participant) {
  const bo = participant?.businessObject || participant || {};
  return bo.id === CONTRACT_PARTICIPANT_ID || participant === CONTRACT_PARTICIPANT_ID;
}

export function isChoreographyTask(element) {
  return element?.type === 'bpmn:ChoreographyTask' || element?.businessObject?.$type === 'bpmn:ChoreographyTask';
}

export function splitRefs(value) {
  if (Array.isArray(value)) {
    return value.filter(Boolean);
  }
  return String(value || '')
    .split(/\s+/)
    .map(item => item.trim())
    .filter(Boolean);
}

export function joinRefs(refs) {
  return Array.from(new Set((refs || []).filter(Boolean))).join(REF_SEPARATOR);
}

export function getExtensionElements(bo, moddle) {
  if (!bo.extensionElements) {
    bo.extensionElements = moddle.create('bpmn:ExtensionElements', {
      values: []
    });
    bo.extensionElements.$parent = bo;
  }
  if (!bo.extensionElements.values) {
    bo.extensionElements.values = [];
  }
  return bo.extensionElements;
}

export function getAssetOperation(element) {
  const values = element?.businessObject?.extensionElements?.values || [];
  return values.find(value => value.$type === ASSET_OPERATION_TYPE) || null;
}

export function ensureAssetOperation(element, moddle) {
  const bo = element.businessObject;
  const extensionElements = getExtensionElements(bo, moddle);
  let operation = getAssetOperation(element);
  if (!operation) {
    operation = moddle.create(ASSET_OPERATION_TYPE, {});
    operation.$parent = extensionElements;
    extensionElements.values.push(operation);
  }
  return operation;
}

export function getAssetOperationData(element) {
  const operation = getAssetOperation(element);
  if (!operation) {
    return {
      operation: '',
      inputAssetRefs: [],
      outputAssetRefs: [],
      recipientRefs: [],
      tokenNumber: '',
      outputs: {}
    };
  }

  const outputs = {};
  (operation.outputs || []).forEach(output => {
    if (output.name) {
      outputs[output.name] = {
        type: output.type || '',
        dataType: output.dataType || 'string'
      };
    }
  });

  return {
    operation: operation.operation || '',
    inputAssetRefs: splitRefs(operation.inputAssetRefs),
    outputAssetRefs: splitRefs(operation.outputAssetRefs),
    recipientRefs: splitRefs(operation.recipientRefs),
    tokenNumber: operation.tokenNumber || '',
    outputs
  };
}

export function updateAssetOperation(element, moddle, modeling, data) {
  const needsExtensionElements = !element.businessObject.extensionElements;
  const operation = ensureAssetOperation(element, moddle);
  if (needsExtensionElements) {
    modeling.updateProperties(element, {
      extensionElements: element.businessObject.extensionElements
    });
  }
  const outputs = Object.entries(data.outputs || {}).map(([name, spec]) => {
    const output = moddle.create('abc:Output', {
      name,
      type: spec.type || '',
      dataType: spec.dataType || 'string'
    });
    output.$parent = operation;
    return output;
  });

  modeling.updateModdleProperties(element, operation, {
    operation: data.operation || '',
    inputAssetRefs: joinRefs(data.inputAssetRefs),
    outputAssetRefs: joinRefs(data.outputAssetRefs),
    recipientRefs: joinRefs(data.recipientRefs),
    tokenNumber: data.tokenNumber || '',
    outputs
  });

  return operation;
}

export function addAssetRef(taskElement, moddle, modeling, kind, assetId) {
  const data = getAssetOperationData(taskElement);
  const key = kind === 'output' ? 'outputAssetRefs' : 'inputAssetRefs';
  data[key] = joinRefs([...data[key], assetId]).split(REF_SEPARATOR).filter(Boolean);
  updateAssetOperation(taskElement, moddle, modeling, data);
}

export function removeAssetRef(taskElement, moddle, modeling, kind, assetId) {
  const data = getAssetOperationData(taskElement);
  const key = kind === 'output' ? 'outputAssetRefs' : 'inputAssetRefs';
  data[key] = data[key].filter(ref => ref !== assetId);
  updateAssetOperation(taskElement, moddle, modeling, data);
}

export function applyAssetOperation(taskElement, moddle, modeling, operation, assetData) {
  const existing = getAssetOperationData(taskElement);
  updateAssetOperation(taskElement, moddle, modeling, {
    ...existing,
    operation,
    tokenNumber: assetData?.assetType === 'transferable' && assetData?.tokenType === 'FT' && operation !== 'query'
      ? existing.tokenNumber
      : '',
    recipientRefs: [],
    outputs: operation === 'query' ? existing.outputs : {}
  });
}

export function getAssetData(assetElement) {
  const bo = assetElement?.businessObject || {};
  return {
    id: bo.id || assetElement?.id,
    assetType: bo.assetType || '',
    tokenType: bo.tokenType || '',
    tokenName: bo.tokenName || '',
    tokenId: bo.tokenId || '',
    tokenURL: bo.tokenURL || '',
    tokenHasExistInERC: Boolean(bo.tokenHasExistInERC)
  };
}

export function getAssetKind(assetElement) {
  const { assetType, tokenType } = getAssetData(assetElement);
  if (assetType === 'transferable') {
    return tokenType === 'FT' ? 'transferable-ft' : 'transferable-nft';
  }
  return assetType || '';
}

export function applyAssetKind(element, modeling, kind) {
  const option = ASSET_KIND_OPTIONS.find(item => item.key === kind);
  if (!option) return;

  modeling.updateProperties(element, {
    assetType: option.assetType,
    tokenType: option.assetType === 'transferable' ? option.tokenType : undefined,
    tokenId: option.key === 'transferable-ft' ? undefined : element.businessObject.tokenId,
    tokenURL: option.assetType === 'distributive' ? element.businessObject.tokenURL : undefined,
    tokenHasExistInERC: option.key === 'transferable-ft' ? undefined : element.businessObject.tokenHasExistInERC,
    documentation: undefined
  });
}

export function applyAssetCategory(element, modeling, assetType) {
  const nextTokenType = assetType === 'transferable'
    ? element.businessObject.tokenType || 'NFT'
    : undefined;

  modeling.updateProperties(element, {
    assetType,
    tokenType: nextTokenType,
    tokenId: assetType === 'transferable' && nextTokenType === 'FT' ? undefined : element.businessObject.tokenId,
    tokenURL: assetType === 'distributive' ? element.businessObject.tokenURL : undefined,
    tokenHasExistInERC: assetType === 'transferable' && nextTokenType === 'FT' ? undefined : element.businessObject.tokenHasExistInERC,
    documentation: undefined
  });
}

export function applyTransferableTokenType(element, modeling, tokenType) {
  modeling.updateProperties(element, {
    assetType: 'transferable',
    tokenType,
    tokenId: tokenType === 'FT' ? undefined : element.businessObject.tokenId,
    tokenURL: undefined,
    tokenHasExistInERC: tokenType === 'FT' ? undefined : element.businessObject.tokenHasExistInERC,
    documentation: undefined
  });
}

export function getDerivedRefTokenIds(assetElement, elementRegistry) {
  if (!assetElement || !elementRegistry) {
    return [];
  }

  const tokenIds = [];
  elementRegistry.getAll().forEach(element => {
    if (!isChoreographyTask(element)) return;

    const operationData = getAssetOperationData(element);
    if (!['branch', 'merge'].includes(operationData.operation)) return;
    if (!operationData.outputAssetRefs.includes(assetElement.id)) return;

    operationData.inputAssetRefs.forEach(assetId => {
      const inputAsset = elementRegistry.get(assetId);
      const tokenId = getAssetData(inputAsset).tokenId;
      if (tokenId) {
        tokenIds.push(tokenId);
      }
    });
  });

  return Array.from(new Set(tokenIds));
}

export function getPrimaryAssetElement(taskElement, elementRegistry) {
  const data = getAssetOperationData(taskElement);
  const createOps = ['mint', 'branch', 'merge'];
  const refs = createOps.includes(data.operation) ? data.outputAssetRefs : data.inputAssetRefs;
  return refs.length ? elementRegistry.get(refs[0]) : null;
}

export function getParticipantOptions(elementRegistry) {
  const toPureParticipantId = id => (id || '').split('_ChoreographyTask_')[0];
  const rawOptions = elementRegistry
    .filter(el => el.businessObject?.$type === 'bpmn:Participant')
    .filter(el => !isContractParticipant(el.businessObject))
    .map(el => {
      const pureId = toPureParticipantId(el.id);
      return {
        value: pureId,
        label: el.businessObject.name || pureId
      };
    });

  return Array.from(new Map(rawOptions.map(item => [item.value, item])).values());
}

export function getReceivingParticipantIds(taskElement) {
  const bo = taskElement?.businessObject;
  const caller = bo?.initiatingParticipantRef?.id || bo?.initiatingParticipantRef || '';
  const receivingIds = (bo?.participantRef || [])
    .filter(participant => !isContractParticipant(participant))
    .map(participant => participant.id || participant)
    .filter(id => id && id !== caller)
    .map(id => id.split('_ChoreographyTask_')[0]);
  return Array.from(new Set(receivingIds));
}
