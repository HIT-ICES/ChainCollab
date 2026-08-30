import { is } from 'bpmn-js/lib/util/ModelUtil';
import {
  getAssetData,
  getAssetOperationData,
  getReceivingParticipantIds,
  isChoreographyTask,
} from '../../../utils/assetExtension';

// 全局缓存，用于存储已计算的状态结果
// 缓存键格式: `${tokenId}:${tokenHasExistInERC}`
// 缓存在每次验证开始时清空
let stateCache = new Map();
let lastValidationRun = 0;

/**
 * Validates AssetTask operations by tracking token state through execution paths.
 *
 * Token State Model:
 * - State: EXISTS or NOT_EXISTS
 * - Initial state: determined by tokenHasExistInERC
 * - State transitions:
 *   - mint: NOT_EXISTS → EXISTS (requires NOT_EXISTS)
 *   - branch: NOT_EXISTS → EXISTS (requires NOT_EXISTS for value-added assets)
 *   - merge: NOT_EXISTS → EXISTS (requires NOT_EXISTS for value-added assets)
 *   - burn: EXISTS → NOT_EXISTS (requires EXISTS)
 *   - transfer/query/grant/revoke: requires EXISTS, no state change
 *
 * @param shape
 * @param reporter {Reporter}
 */
export default function assetTaskOperationConstraint(shape, reporter) {
  // 每次验证运行时清空缓存（通过检测时间戳变化）
  const now = Date.now();
  if (now - lastValidationRun > 100) {
    stateCache.clear();
    lastValidationRun = now;
  }

  if (isChoreographyTask(shape)) {
    const taskConfig = getAssetOperationData(shape);
    const { operation } = taskConfig;
    if (!operation) return;

    const linkedAsset = getLinkedAssetFromRefs(taskConfig, reporter.elementRegistry);
    if (!linkedAsset) {
      reporter.error(
        shape,
        `AssetOperation with operation <b>${operation}</b> must reference an Asset. ` +
        `Please connect an Asset input or output according to the operation type.`
      );
      return;
    }

    const { assetType, tokenType, tokenId, tokenHasExistInERC } = linkedAsset;
    if (!validateOperationAssetTypeMatch(shape, operation, assetType, tokenType, reporter)) {
      return;
    }

    const receivingParticipantIds = getReceivingParticipantIds(shape);
    const multiCalleeOperations = ['grant usage rights', 'revoke usage rights'];
    const singleCalleeOperations = ['Transfer', 'transfer'];
    const calleeFreeOperations = ['mint', 'burn', 'query', 'branch', 'merge'];

    if (multiCalleeOperations.includes(operation) && receivingParticipantIds.length === 0) {
      reporter.error(
        shape,
        `<b>${operation}</b> requires at least one non-initiating participant.`
      );
      return;
    }

    if (singleCalleeOperations.includes(operation) && receivingParticipantIds.length !== 1) {
      reporter.error(
        shape,
        `<b>${operation}</b> requires exactly one non-initiating participant.`
      );
      return;
    }

    if (calleeFreeOperations.includes(operation) && receivingParticipantIds.length > 0) {
      reporter.error(
        shape,
        `<b>${operation}</b> must not have non-initiating business participants. Keep only the Contract placeholder.`
      );
      return;
    }

    if (!['grant usage rights', 'revoke usage rights'].includes(operation) && taskConfig.recipientRefs.length > 0) {
      reporter.error(
        shape,
        `<b>${operation}</b> must not use recipientRefs. Recipients are derived from non-initiating participant bands.`
      );
      return;
    }

    if (assetType === 'transferable' && tokenType === 'FT') return;
    if (!tokenId) return;
    validateOperationWithStateTracking(shape, tokenId, operation, tokenHasExistInERC, assetType, reporter);
    return;
  }

  // Only check legacy Task elements
  if (!is(shape, 'bpmn:Task')) {
    return;
  }

  // Get task documentation
  const docs = shape.businessObject.documentation;
  if (!Array.isArray(docs) || docs.length === 0) {
    return;
  }

  let taskConfig;
  try {
    taskConfig = JSON.parse(docs[0].text);
  } catch {
    return;
  }

  // Get linked DataObject asset information
  const linkedAsset = getLinkedDataObjectAsset(shape, reporter.elementRegistry);

  // Check if Task has an operation defined
  const { operation } = taskConfig;
  if (!operation) {
    // Only report error if the Task has documentation (meaning it's an AssetTask)
    if (taskConfig.assetType || taskConfig.tokenType || taskConfig.tokenName) {
      reporter.error(
        shape,
        `AssetTask must have an operation defined. ` +
        `Please configure the operation type (mint, transfer, burn, etc.) in the Task properties.`
      );
    }
    return;
  }

  // Check if Task is connected to a DataObject
  if (!linkedAsset) {
    reporter.error(
      shape,
      `AssetTask with operation <b>${operation}</b> must be connected to a DataObject. ` +
      `Please add a DataInputAssociation (DataObject → Task) or DataOutputAssociation (Task → DataObject) connection.`
    );
    return;
  }

  const { assetType, tokenType, tokenId, tokenHasExistInERC } = linkedAsset;

  // Validate operation type matches asset type
  if (!validateOperationAssetTypeMatch(shape, operation, assetType, tokenType, reporter)) {
    return;
  }

  // Skip validation for FT (no restrictions on operation sequence)
  if (assetType === 'transferable' && tokenType === 'FT') {
    return;
  }

  // Skip if no tokenId (can't track operations)
  if (!tokenId) {
    return;
  }

  // Validate operation based on token state tracking
  validateOperationWithStateTracking(shape, tokenId, operation, tokenHasExistInERC, assetType, reporter);
}

function getLinkedAssetFromRefs(taskConfig, elementRegistry) {
  const createOps = ['mint', 'branch', 'merge'];
  const refs = createOps.includes(taskConfig.operation)
    ? taskConfig.outputAssetRefs
    : taskConfig.inputAssetRefs;
  const assetElement = refs.length ? elementRegistry.get(refs[0]) : null;
  return assetElement ? getAssetData(assetElement) : null;
}

/**
 * Get linked DataObject asset information from Task connections
 */
function getLinkedDataObjectAsset(taskShape, elementRegistry) {
  const incoming = taskShape.incoming || [];
  const outgoing = taskShape.outgoing || [];
  const allConnections = [...incoming, ...outgoing];

  // Check DataOutputAssociation (Task -> DataObject)
  for (const connection of allConnections) {
    const connBo = connection.businessObject;
    if (connBo.$type === 'bpmn:DataOutputAssociation') {
      const dataObjectElement = connection.target;
      if (dataObjectElement && dataObjectElement.type === 'bpmn:DataObjectReference') {
        const docs = dataObjectElement.businessObject.documentation;
        if (Array.isArray(docs) && docs.length) {
          try {
            return JSON.parse(docs[0].text);
          } catch {
            // ignore
          }
        }
      }
    }
  }

  // Check DataInputAssociation (DataObject -> Task)
  for (const connection of allConnections) {
    const connBo = connection.businessObject;
    if (connBo.$type === 'bpmn:DataInputAssociation') {
      const dataObjectElement = connection.source;
      if (dataObjectElement && dataObjectElement.type === 'bpmn:DataObjectReference') {
        const docs = dataObjectElement.businessObject.documentation;
        if (Array.isArray(docs) && docs.length) {
          try {
            return JSON.parse(docs[0].text);
          } catch {
            // ignore
          }
        }
      }
    }
  }

  return null;
}

/**
 * Validate that operation type matches asset type
 */
function validateOperationAssetTypeMatch(shape, operation, assetType, tokenType, reporter) {
  const operationLower = operation.toLowerCase();

  // Define valid operations for each asset type
  const validOperations = {
    'distributive': ['mint', 'burn', 'grant usage rights', 'revoke usage rights', 'transfer', 'query'],
    'transferable': ['mint', 'burn', 'transfer', 'query'],
    'value-added': ['branch', 'merge', 'transfer', 'burn', 'query']
  };

  // Get valid operations for this asset type
  const validOps = validOperations[assetType] || [];
  const validOpsLower = validOps.map(op => op.toLowerCase());

  // Check if operation is valid for this asset type
  if (!validOpsLower.includes(operationLower)) {
    const assetTypeDisplay = assetType === 'transferable' && tokenType
      ? `${assetType} (${tokenType})`
      : assetType;

    reporter.error(
      shape,
      `Operation <b>${operation}</b> is not valid for asset type <b>${assetTypeDisplay}</b>. ` +
      `Valid operations for this asset type are: <b>${validOps.join(', ')}</b>.`
    );
    return false;
  }

  return true;
}

/**
 * Validate operation by tracking token state through all execution paths
 */
function validateOperationWithStateTracking(currentShape, tokenId, currentOperation, tokenHasExistInERC, assetType, reporter) {
  // Get all possible states when reaching this task
  const possibleStates = getPossibleStatesAtTask(currentShape, tokenId, tokenHasExistInERC, reporter.elementRegistry);

  // Check if operation is valid in any of the possible states
  const operationLower = currentOperation.toLowerCase();

  // Define which operations require which state
  const requiresExists = ['transfer', 'burn', 'query', 'grant usage rights', 'revoke usage rights'];
  const requiresNotExists = ['mint'];

  if (requiresNotExists.includes(operationLower)) {
    // mint requires NOT_EXISTS state
    if (!possibleStates.has('NOT_EXISTS')) {
      reporter.error(
        currentShape,
        `Cannot mint tokenId <b>${tokenId}</b> because the token already exists at this point in the execution flow. ` +
        `Mint operation requires the token to not exist. ` +
        `Possible states at this task: <b>${Array.from(possibleStates).join(', ')}</b>.`
      );
    }
  } else if (requiresExists.includes(operationLower)) {
    // transfer/burn/query/grant/revoke require EXISTS state
    if (!possibleStates.has('EXISTS')) {
      reporter.error(
        currentShape,
        `Cannot ${currentOperation} tokenId <b>${tokenId}</b> because the token does not exist at this point in the execution flow. ` +
        `This operation requires the token to exist (must be minted first). ` +
        `Possible states at this task: <b>${Array.from(possibleStates).join(', ')}</b>.`
      );
    }
  }

  // Special validation for value-added assets
  if (assetType === 'value-added' && (operationLower === 'branch' || operationLower === 'merge')) {
    // branch/merge operations require NOT_EXISTS state (similar to mint)
    if (!possibleStates.has('NOT_EXISTS')) {
      reporter.error(
        currentShape,
        `Cannot ${currentOperation} tokenId <b>${tokenId}</b> because the token already exists at this point in the execution flow. ` +
        `Branch and merge operations require the token to not exist (similar to mint operation). ` +
        `Possible states at this task: <b>${Array.from(possibleStates).join(', ')}</b>.`
      );
    }

    validateValueAddedOperation(currentShape, tokenId, currentOperation, tokenHasExistInERC, reporter);
  }
}

/**
 * Get all possible token states when reaching a specific task
 * Returns a Set of possible states: 'EXISTS', 'NOT_EXISTS', or both
 * 使用缓存优化性能
 */
function getPossibleStatesAtTask(targetTask, tokenId, tokenHasExistInERC, elementRegistry) {
  // 生成缓存键
  const cacheKey = `${targetTask.id}:${tokenId}:${tokenHasExistInERC}`;

  // 检查缓存
  if (stateCache.has(cacheKey)) {
    return stateCache.get(cacheKey);
  }

  const initialState = tokenHasExistInERC ? 'EXISTS' : 'NOT_EXISTS';
  const visited = new Map(); // Map<elementId, Set<states>>
  const possibleStates = new Set();

  // Find all start events
  const startEvents = [];
  elementRegistry.forEach(element => {
    if (is(element, 'bpmn:StartEvent')) {
      startEvents.push(element);
    }
  });

  // If no start events, start from elements with no incoming flows
  if (startEvents.length === 0) {
    elementRegistry.forEach(element => {
      const incoming = element.incoming || [];
      const hasSequenceFlowIncoming = incoming.some(conn =>
        conn.businessObject.$type === 'bpmn:SequenceFlow'
      );
      if (!hasSequenceFlowIncoming && element.id !== targetTask.id) {
        startEvents.push(element);
      }
    });
  }

  // 限制最大迭代次数，防止复杂图导致的性能问题
  let iterationCount = 0;
  const MAX_ITERATIONS = 1000;

  // DFS from each start event
  function dfs(element, currentState) {
    // 防止无限循环
    if (++iterationCount > MAX_ITERATIONS) {
      return;
    }

    // If we reached the target task, record the state
    if (element.id === targetTask.id) {
      possibleStates.add(currentState);
      return;
    }

    // Check if we've visited this element with this state
    if (visited.has(element.id)) {
      const states = visited.get(element.id);
      if (states.has(currentState)) {
        return; // Already explored this path
      }
      states.add(currentState);
    } else {
      visited.set(element.id, new Set([currentState]));
    }

    // Update state based on current element's operation
    let newState = currentState;
    if (isChoreographyTask(element)) {
      const taskConfig = getAssetOperationData(element);
      const linkedAsset = getLinkedAssetFromRefs(taskConfig, elementRegistry);

      if (linkedAsset && linkedAsset.tokenId === tokenId && taskConfig.operation) {
        const op = taskConfig.operation.toLowerCase();
        if (op === 'mint' || op === 'branch' || op === 'merge') {
          newState = 'EXISTS';
        } else if (op === 'burn') {
          newState = 'NOT_EXISTS';
        }
      }
    } else if (is(element, 'bpmn:Task')) {
      const docs = element.businessObject.documentation;
      if (Array.isArray(docs) && docs.length > 0) {
        try {
          const taskConfig = JSON.parse(docs[0].text);
          const linkedAsset = getLinkedDataObjectAsset(element, elementRegistry);

          if (linkedAsset && linkedAsset.tokenId === tokenId && taskConfig.operation) {
            const op = taskConfig.operation.toLowerCase();
            if (op === 'mint' || op === 'branch' || op === 'merge') {
              newState = 'EXISTS';
            } else if (op === 'burn') {
              newState = 'NOT_EXISTS';
            }
            // transfer/query/grant/revoke don't change state
          }
        } catch {
          // ignore
        }
      }
    }

    // Follow outgoing sequence flows
    const outgoing = element.outgoing || [];
    for (const flow of outgoing) {
      if (flow.businessObject.$type === 'bpmn:SequenceFlow') {
        const target = flow.target;
        if (target) {
          dfs(target, newState);
        }
      }
    }
  }

  // Start DFS from all start points
  if (startEvents.length > 0) {
    for (const startEvent of startEvents) {
      dfs(startEvent, initialState);
    }
  } else {
    // If no start events found, assume initial state at target
    possibleStates.add(initialState);
  }

  // If no states found (target not reachable), return initial state
  if (possibleStates.size === 0) {
    possibleStates.add(initialState);
  }

  // 存入缓存
  stateCache.set(cacheKey, possibleStates);

  return possibleStates;
}

/**
 * Validate value-added operations (branch/merge)
 */
function validateValueAddedOperation(currentShape, tokenId, currentOperation, tokenHasExistInERC, reporter) {
  let refTokenIds = [];

  if (isChoreographyTask(currentShape)) {
    const taskConfig = getAssetOperationData(currentShape);
    refTokenIds = (taskConfig.inputAssetRefs || [])
      .map(assetId => {
        const assetElement = reporter.elementRegistry.get(assetId);
        return assetElement ? getAssetData(assetElement).tokenId : '';
      })
      .filter(Boolean);
  } else {
    const linkedAsset = getLinkedDataObjectAsset(currentShape, reporter.elementRegistry);
    refTokenIds = linkedAsset?.refTokenIds || [];
  }

  if (refTokenIds.length > 0) {
    refTokenIds.forEach(refTokenId => {
      // Check if referenced token exists at this point
      const refStates = getPossibleStatesAtTask(currentShape, refTokenId, false, reporter.elementRegistry);

      // Check if referenced token has tokenHasExistInERC
      let refHasExistInERC = false;
      reporter.elementRegistry.forEach(element => {
        if (element.type === 'abc:Asset') {
          const parsed = getAssetData(element);
          if (parsed.tokenId === refTokenId && parsed.tokenHasExistInERC) {
            refHasExistInERC = true;
          }
        } else if (element.type === 'bpmn:DataObjectReference') {
          const docs = element.businessObject.documentation;
          if (Array.isArray(docs) && docs.length) {
            try {
              const parsed = JSON.parse(docs[0].text);
              if (parsed.tokenId === refTokenId && parsed.tokenHasExistInERC) {
                refHasExistInERC = true;
              }
            } catch {
              // ignore
            }
          }
        }
      });

      // If refHasExistInERC is true, the token always exists
      if (refHasExistInERC) {
        return; // Valid
      }

      // Check if referenced token exists
      if (!refStates.has('EXISTS')) {
        reporter.error(
          currentShape,
          `Cannot ${currentOperation} with reference to tokenId <b>${refTokenId}</b> because it does not exist at this point. ` +
          `Referenced token must be minted before this operation. ` +
          `Possible states of referenced token: <b>${Array.from(refStates).join(', ')}</b>.`
        );
      }
    });
  }
}
