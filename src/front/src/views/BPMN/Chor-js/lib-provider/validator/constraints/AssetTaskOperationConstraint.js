import { is } from 'bpmn-js/lib/util/ModelUtil';

/**
 * Validates AssetTask operations by tracking token state through execution paths.
 *
 * Token State Model:
 * - State: EXISTS or NOT_EXISTS
 * - Initial state: determined by tokenHasExistInERC
 * - State transitions:
 *   - mint: NOT_EXISTS → EXISTS
 *   - burn: EXISTS → NOT_EXISTS
 *   - transfer/query/grant/revoke: requires EXISTS, no state change
 *
 * @param shape
 * @param reporter {Reporter}
 */
export default function assetTaskOperationConstraint(shape, reporter) {
  // Only check Task elements
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
    'value-added': ['branch', 'merge', 'transfer', 'query']
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
    validateValueAddedOperation(currentShape, tokenId, currentOperation, tokenHasExistInERC, reporter);
  }
}

/**
 * Get all possible token states when reaching a specific task
 * Returns a Set of possible states: 'EXISTS', 'NOT_EXISTS', or both
 */
function getPossibleStatesAtTask(targetTask, tokenId, tokenHasExistInERC, elementRegistry) {
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

  // DFS from each start event
  function dfs(element, currentState) {
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
    if (is(element, 'bpmn:Task')) {
      const docs = element.businessObject.documentation;
      if (Array.isArray(docs) && docs.length > 0) {
        try {
          const taskConfig = JSON.parse(docs[0].text);
          const linkedAsset = getLinkedDataObjectAsset(element, elementRegistry);

          if (linkedAsset && linkedAsset.tokenId === tokenId && taskConfig.operation) {
            const op = taskConfig.operation.toLowerCase();
            if (op === 'mint') {
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

  return possibleStates;
}

/**
 * Validate value-added operations (branch/merge)
 */
function validateValueAddedOperation(currentShape, tokenId, currentOperation, tokenHasExistInERC, reporter) {
  const linkedAsset = getLinkedDataObjectAsset(currentShape, reporter.elementRegistry);
  const refTokenIds = linkedAsset?.refTokenIds || [];

  if (refTokenIds.length > 0) {
    refTokenIds.forEach(refTokenId => {
      // Check if referenced token exists at this point
      const refStates = getPossibleStatesAtTask(currentShape, refTokenId, false, reporter.elementRegistry);

      // Check if referenced token has tokenHasExistInERC
      let refHasExistInERC = false;
      reporter.elementRegistry.forEach(element => {
        if (element.type === 'bpmn:DataObjectReference') {
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
