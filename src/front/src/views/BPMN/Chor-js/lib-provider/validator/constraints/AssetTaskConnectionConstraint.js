import { is } from 'bpmn-js/lib/util/ModelUtil';

/**
 * Validates that AssetTask elements have correct DataObject connections based on operation type.
 *
 * Connection rules:
 * - mint: Requires DataOutputAssociation (Task -> DataObject) - creates new token
 * - branch: Requires DataInputAssociation (DataObject -> Task) + DataOutputAssociation (Task -> DataObject)
 * - merge: Requires multiple DataInputAssociation + DataOutputAssociation
 * - transfer: Requires DataInputAssociation (reads token to transfer)
 * - burn: Requires DataInputAssociation (reads token to burn)
 * - query: Requires DataInputAssociation (reads token to query)
 * - grant/revoke usage rights: Requires DataInputAssociation (reads token to modify permissions)
 *
 * @param shape
 * @param reporter {Reporter}
 */
export default function assetTaskConnectionConstraint(shape, reporter) {
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

  const { operation } = taskConfig;

  // Skip if no operation defined
  if (!operation) {
    return;
  }

  // Count connections
  const incoming = shape.incoming || [];
  const outgoing = shape.outgoing || [];

  let inputAssociationCount = 0;
  let outputAssociationCount = 0;

  // Count DataInputAssociation (DataObject -> Task)
  incoming.forEach(connection => {
    const connBo = connection.businessObject;
    if (connBo.$type === 'bpmn:DataInputAssociation') {
      const source = connection.source;
      if (source && source.type === 'bpmn:DataObjectReference') {
        inputAssociationCount++;
      }
    }
  });

  // Count DataOutputAssociation (Task -> DataObject)
  outgoing.forEach(connection => {
    const connBo = connection.businessObject;
    if (connBo.$type === 'bpmn:DataOutputAssociation') {
      const target = connection.target;
      if (target && target.type === 'bpmn:DataObjectReference') {
        outputAssociationCount++;
      }
    }
  });

  // Validate based on operation type
  validateConnectionsByOperation(
    shape,
    operation,
    inputAssociationCount,
    outputAssociationCount,
    reporter
  );
}

/**
 * Validate connections based on operation type
 */
function validateConnectionsByOperation(shape, operation, inputCount, outputCount, reporter) {
  const operationLower = operation.toLowerCase();

  // Rule 1: mint operation requires output connection
  if (operationLower === 'mint') {
    if (outputCount === 0) {
      reporter.error(
        shape,
        `<b>mint</b> operation requires a DataOutputAssociation (Task → DataObject). ` +
        `Please connect this Task to a DataObject using an output association to represent the newly minted token.`
      );
      return;
    }
    if (outputCount > 1) {
      reporter.warn(
        shape,
        `<b>mint</b> operation has ${outputCount} output connections. ` +
        `Typically, mint should create only one token (one DataObject output).`
      );
    }
  }

  // Rule 2: branch operation requires input + output connections
  if (operationLower === 'branch') {
    if (inputCount === 0) {
      reporter.error(
        shape,
        `<b>branch</b> operation requires at least one DataInputAssociation (DataObject → Task). ` +
        `Please connect source DataObject(s) to this Task to specify which tokens to branch from.`
      );
    }
    if (outputCount === 0) {
      reporter.error(
        shape,
        `<b>branch</b> operation requires a DataOutputAssociation (Task → DataObject). ` +
        `Please connect this Task to a DataObject to represent the newly branched token.`
      );
    }
    if (outputCount > 1) {
      reporter.warn(
        shape,
        `<b>branch</b> operation has ${outputCount} output connections. ` +
        `Typically, branch should create only one derived token (one DataObject output).`
      );
    }
  }

  // Rule 3: merge operation requires multiple inputs + output connection
  if (operationLower === 'merge') {
    if (inputCount === 0) {
      reporter.error(
        shape,
        `<b>merge</b> operation requires multiple DataInputAssociation connections (DataObject → Task). ` +
        `Please connect source DataObject(s) to this Task to specify which tokens to merge.`
      );
    }
    if (inputCount === 1) {
      reporter.warn(
        shape,
        `<b>merge</b> operation typically requires multiple input tokens. ` +
        `Currently only ${inputCount} DataInputAssociation found. Consider adding more source tokens to merge.`
      );
    }
    if (outputCount === 0) {
      reporter.error(
        shape,
        `<b>merge</b> operation requires a DataOutputAssociation (Task → DataObject). ` +
        `Please connect this Task to a DataObject to represent the merged token.`
      );
    }
    if (outputCount > 1) {
      reporter.warn(
        shape,
        `<b>merge</b> operation has ${outputCount} output connections. ` +
        `Typically, merge should create only one merged token (one DataObject output).`
      );
    }
  }

  // Rule 4: transfer operation requires input connection
  if (operationLower === 'transfer') {
    if (inputCount === 0) {
      reporter.error(
        shape,
        `<b>transfer</b> operation requires a DataInputAssociation (DataObject → Task). ` +
        `Please connect a DataObject to this Task to specify which token to transfer.`
      );
      return;
    }
    if (inputCount > 1) {
      reporter.warn(
        shape,
        `<b>transfer</b> operation has ${inputCount} input connections. ` +
        `Typically, transfer operates on one token at a time.`
      );
    }
    // Transfer typically doesn't create new DataObject, so no output validation
  }

  // Rule 5: burn operation requires input connection
  if (operationLower === 'burn') {
    if (inputCount === 0) {
      reporter.error(
        shape,
        `<b>burn</b> operation requires a DataInputAssociation (DataObject → Task). ` +
        `Please connect a DataObject to this Task to specify which token to burn.`
      );
      return;
    }
    if (inputCount > 1) {
      reporter.warn(
        shape,
        `<b>burn</b> operation has ${inputCount} input connections. ` +
        `Typically, burn operates on one token at a time.`
      );
    }
    // Burn destroys the token, so no output validation
  }

  // Rule 6: query operation requires input connection
  if (operationLower === 'query') {
    if (inputCount === 0) {
      reporter.error(
        shape,
        `<b>query</b> operation requires a DataInputAssociation (DataObject → Task). ` +
        `Please connect a DataObject to this Task to specify which token to query.`
      );
      return;
    }
    if (inputCount > 1) {
      reporter.warn(
        shape,
        `<b>query</b> operation has ${inputCount} input connections. ` +
        `Typically, query operates on one token at a time.`
      );
    }
    // Query is read-only, so no output validation
  }

  // Rule 7: grant/revoke usage rights operations require input connection
  if (operationLower === 'grant usage rights' || operationLower === 'revoke usage rights') {
    if (inputCount === 0) {
      reporter.error(
        shape,
        `<b>${operation}</b> operation requires a DataInputAssociation (DataObject → Task). ` +
        `Please connect a DataObject to this Task to specify which token's permissions to modify.`
      );
      return;
    }
    if (inputCount > 1) {
      reporter.warn(
        shape,
        `<b>${operation}</b> operation has ${inputCount} input connections. ` +
        `Typically, permission operations work on one token at a time.`
      );
    }
    // Permission operations modify existing token, so no output validation
  }
}
