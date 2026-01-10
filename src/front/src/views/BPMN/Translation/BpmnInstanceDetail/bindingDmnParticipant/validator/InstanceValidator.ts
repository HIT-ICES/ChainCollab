/**
 * Instance Validator
 * Validates token ownership and caller permissions during instance creation
 */

export interface ValidationError {
  taskId: string;
  taskName: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

export interface ParticipantBinding {
  selectedValidationType: string;
  selectedMembershipId?: string;
  selectedUser?: string;
  Attr?: Array<{ attr: string; value: string }>;
}

export interface TaskERCInfo {
  tokenName: string;
  [key: string]: any;
}

/**
 * Validates token operations against participant bindings
 * @param bpmnXml - The BPMN XML content
 * @param participantBindings - Map of participant ID to binding information
 * @param taskERCMap - Map of task ID to ERC/token information
 * @param bpmnFireflyUrl - Optional firefly URL from BPMN for blockchain queries (format: http://host:port/api/v1/namespaces/default/apis/contractName)
 * @returns Validation result with errors
 */
export async function validateInstance(
  bpmnXml: string,
  participantBindings: Map<string, ParticipantBinding>,
  taskERCMap: Record<string, TaskERCInfo>,
  bpmnFireflyUrl?: string
): Promise<ValidationResult> {
  console.log('[InstanceValidator] Starting validation...');
  console.log('[InstanceValidator] Participant bindings size:', participantBindings?.size);
  console.log('[InstanceValidator] Task ERC map keys:', Object.keys(taskERCMap || {}));

  const errors: ValidationError[] = [];

  try {
    // Parse BPMN XML
    console.log('[InstanceValidator] Parsing BPMN XML...');
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(bpmnXml, 'text/xml');

    // Check for XML parsing errors
    const parserError = xmlDoc.querySelector('parsererror');
    if (parserError) {
      console.error('[InstanceValidator] XML parsing error:', parserError.textContent);
      throw new Error('Failed to parse BPMN XML');
    }

    // Find all tasks with asset operations
    const tasks = xmlDoc.querySelectorAll('bpmn\\:task, task, bpmn\\:userTask, userTask, bpmn\\:serviceTask, serviceTask');
    console.log('[InstanceValidator] Found tasks:', tasks.length);

    // ===== STEP 1: Scan all DataObjectReferences to build token registry =====
    const dataObjects = xmlDoc.querySelectorAll('bpmn\\:dataObjectReference, dataObjectReference');
    console.log('[InstanceValidator] Found DataObjects:', dataObjects.length);

    // Track token types - built from DataObject definitions
    const tokenTypeRegistry = new Map<string, { tokenType: string; tokenName: string; tokenId?: string; assetType?: string; tokenHasExistInERC?: boolean }>();

    dataObjects.forEach((dataObj, index) => {
      const dataObjId = dataObj.getAttribute('id');
      const dataObjName = dataObj.getAttribute('name') || dataObjId;
      console.log(`[InstanceValidator] Processing DataObject ${index + 1}/${dataObjects.length}: ${dataObjName} (${dataObjId})`);

      const documentation = dataObj.querySelector('bpmn\\:documentation, documentation');
      if (documentation) {
        try {
          const dataObjInfo = JSON.parse(documentation.textContent || '{}');
          const { assetType, tokenType, tokenName, tokenId, tokenHasExistInERC } = dataObjInfo;

          if (tokenName) {
            // Use tokenId if available, otherwise use tokenName as identifier
            const tokenIdentifier = tokenId ? tokenId.toString() : tokenName;

            // Register this token's definition from DataObject
            tokenTypeRegistry.set(tokenIdentifier, {
              tokenType: tokenType || (tokenId ? 'NFT' : 'FT'), // Infer if not specified
              tokenName,
              tokenId,
              assetType,
              tokenHasExistInERC: tokenHasExistInERC || false
            });

            console.log(`[InstanceValidator] Registered DataObject token: "${tokenIdentifier}" -> Type: ${tokenType || (tokenId ? 'NFT' : 'FT')}, Name: ${tokenName}, HasExistInERC: ${tokenHasExistInERC || false}`);
          }
        } catch (parseError) {
          console.log(`[InstanceValidator] Failed to parse DataObject ${dataObjName} documentation`);
        }
      }
    });

    console.log('[InstanceValidator] Token registry built from DataObjects:', Array.from(tokenTypeRegistry.entries()));

    // ===== STEP 2: Build Task -> DataObject mapping =====
    const taskToDataObjectMap = new Map<string, Set<string>>(); // taskId -> Set of dataObjectIds

    // Find all data associations (input and output)
    const dataInputAssociations = xmlDoc.querySelectorAll('bpmn\\:dataInputAssociation, dataInputAssociation');
    const dataOutputAssociations = xmlDoc.querySelectorAll('bpmn\\:dataOutputAssociation, dataOutputAssociation');

    console.log('[InstanceValidator] Found DataInputAssociations:', dataInputAssociations.length);
    console.log('[InstanceValidator] Found DataOutputAssociations:', dataOutputAssociations.length);

    // Process input associations
    dataInputAssociations.forEach(assoc => {
      const sourceRef = assoc.querySelector('bpmn\\:sourceRef, sourceRef');
      if (sourceRef) {
        const dataObjectId = sourceRef.textContent?.trim();
        const parentTask = assoc.parentElement;
        if (dataObjectId && parentTask) {
          const taskId = parentTask.getAttribute('id');
          if (taskId) {
            if (!taskToDataObjectMap.has(taskId)) {
              taskToDataObjectMap.set(taskId, new Set());
            }
            taskToDataObjectMap.get(taskId)!.add(dataObjectId);
            console.log(`[InstanceValidator] Task ${taskId} reads from DataObject ${dataObjectId}`);
          }
        }
      }
    });

    // Process output associations
    dataOutputAssociations.forEach(assoc => {
      const targetRef = assoc.querySelector('bpmn\\:targetRef, targetRef');
      if (targetRef) {
        const dataObjectId = targetRef.textContent?.trim();
        const parentTask = assoc.parentElement;
        if (dataObjectId && parentTask) {
          const taskId = parentTask.getAttribute('id');
          if (taskId) {
            if (!taskToDataObjectMap.has(taskId)) {
              taskToDataObjectMap.set(taskId, new Set());
            }
            taskToDataObjectMap.get(taskId)!.add(dataObjectId);
            console.log(`[InstanceValidator] Task ${taskId} writes to DataObject ${dataObjectId}`);
          }
        }
      }
    });

    console.log('[InstanceValidator] Task to DataObject mapping:', Array.from(taskToDataObjectMap.entries()));

    // ===== STEP 3: Build execution order based on BPMN flow =====
    console.log('[InstanceValidator] Building task execution order from BPMN flow...');

    // Build flow graph: taskId -> list of next taskIds
    const flowGraph = new Map<string, string[]>();
    const incomingCount = new Map<string, number>();
    const taskMap = new Map<string, Element>();

    // Initialize task map and incoming count
    tasks.forEach(task => {
      const taskId = task.getAttribute('id');
      if (taskId) {
        taskMap.set(taskId, task);
        if (!incomingCount.has(taskId)) {
          incomingCount.set(taskId, 0);
        }
        if (!flowGraph.has(taskId)) {
          flowGraph.set(taskId, []);
        }
      }
    });

    // Find all sequence flows
    const sequenceFlows = xmlDoc.querySelectorAll('bpmn\\:sequenceFlow, sequenceFlow');
    console.log(`[InstanceValidator] Found ${sequenceFlows.length} sequence flows`);

    sequenceFlows.forEach(flow => {
      const sourceRef = flow.getAttribute('sourceRef');
      const targetRef = flow.getAttribute('targetRef');

      if (sourceRef && targetRef) {
        // Only track flows between tasks (ignore gateways, events, etc.)
        if (taskMap.has(sourceRef) && taskMap.has(targetRef)) {
          if (!flowGraph.has(sourceRef)) {
            flowGraph.set(sourceRef, []);
          }
          flowGraph.get(sourceRef)!.push(targetRef);
          incomingCount.set(targetRef, (incomingCount.get(targetRef) || 0) + 1);
          console.log(`[InstanceValidator] Flow: ${sourceRef} -> ${targetRef}`);
        }
      }
    });

    // Topological sort to get execution order
    const executionOrder: string[] = [];
    const queue: string[] = [];

    // Find all tasks with no incoming flows (start tasks)
    incomingCount.forEach((count, taskId) => {
      if (count === 0) {
        queue.push(taskId);
        console.log(`[InstanceValidator] Start task found: ${taskId}`);
      }
    });

    // Process tasks in topological order
    while (queue.length > 0) {
      const currentTaskId = queue.shift()!;
      executionOrder.push(currentTaskId);

      const nextTasks = flowGraph.get(currentTaskId) || [];
      nextTasks.forEach(nextTaskId => {
        const newCount = (incomingCount.get(nextTaskId) || 0) - 1;
        incomingCount.set(nextTaskId, newCount);
        if (newCount === 0) {
          queue.push(nextTaskId);
        }
      });
    }

    // Add any remaining tasks that weren't in the flow (isolated tasks)
    taskMap.forEach((task, taskId) => {
      if (!executionOrder.includes(taskId)) {
        executionOrder.push(taskId);
        console.log(`[InstanceValidator] Isolated task added: ${taskId}`);
      }
    });

    console.log('[InstanceValidator] Task execution order:', executionOrder);
    console.log(`[InstanceValidator] Total tasks to process: ${executionOrder.length}`);

    // ===== STEP 4: Process tasks in execution order using the token registry from DataObjects =====
    // Track token ownership through the process flow
    const tokenOwnership = new Map<string, string[]>(); // tokenId -> list of participant IDs who own it

    // Track which ERC contract each token is bound to
    const tokenERCBinding = new Map<string, { ercId: string; ercName: string; taskId: string; taskName: string }>();

    // Track burned tokens (NFT only - FT can be re-minted)
    const burnedTokens = new Map<string, { taskName: string; taskId: string }>();

    // Track minted tokens (NFT only - to prevent duplicate minting)
    // Key: tokenIdentifier, Value: { taskName, taskId, operation }
    const mintedTokens = new Map<string, { taskName: string; taskId: string; operation: string }>();

    // ===== IMPORTANT: Pre-mint tokens that have tokenHasExistInERC = true =====
    // These tokens are already minted in the ERC contract, so we need to establish initial ownership
    console.log('[InstanceValidator] ===== Pre-minting tokens with tokenHasExistInERC = true =====');

    // Need to process this asynchronously since we're querying the blockchain
    const preMintPromises: Promise<void>[] = [];

    // Extract base firefly URL if provided
    const basefirelfyUrl = bpmnFireflyUrl ? bpmnFireflyUrl.slice(0, bpmnFireflyUrl.lastIndexOf('/apis/')) : null;
    console.log('[InstanceValidator] Base Firefly URL:', basefirelfyUrl);

    tokenTypeRegistry.forEach((tokenInfo, tokenIdentifier) => {
      if (tokenInfo.tokenHasExistInERC && tokenInfo.tokenType !== 'FT') {
        const preMintTask = (async () => {
          // Find the ERC chaincode URL from taskERCMap
          // We need to find a task that uses this token
          let ercChaincodeUrl: string | null = null;

          for (const [_, ercInfo] of Object.entries(taskERCMap)) {
            // Check if this task uses the current token
            if (ercInfo.tokenName === tokenInfo.tokenName) {
              // Extract ERC chaincode name from the task
              const ercNameKey = Object.keys(ercInfo).find(k => k.endsWith('_ERCName'));
              if (ercNameKey && basefirelfyUrl) {
                const ercName = ercInfo[ercNameKey];
                // Construct the chaincode URL
                // Format: {basefirelfyUrl}/apis/{ercName}
                ercChaincodeUrl = `${basefirelfyUrl}/apis/${ercName}`;
                console.log(`[InstanceValidator] Constructed ERC chaincode URL for token ${tokenIdentifier}: ${ercChaincodeUrl}`);
              }
              break;
            }
          }

          if (!ercChaincodeUrl) {
            console.error(`[InstanceValidator] CRITICAL: Token "${tokenIdentifier}" (${tokenInfo.tokenName}) is marked as existing in ERC but no ERC contract binding found`);
            errors.push({
              taskId: 'PRE_MINT_' + tokenIdentifier,
              taskName: `Pre-existing Token: ${tokenInfo.tokenName}`,
              message: `Token "${tokenInfo.tokenName}" (ID: ${tokenIdentifier}) is marked as already existing in ERC contract (tokenHasExistInERC=true), but no task is bound to an ERC contract for this token. Please bind at least one task using this token to an ERC contract in "Binding Tasks to ERC".`,
              severity: 'error'
            });
            return;
          }

          // Query blockchain for owner
          const ownerParticipantId = await findParticipantByBlockchainIdentity(
            participantBindings,
            tokenIdentifier,
            tokenInfo,
            ercChaincodeUrl
          );

          if (ownerParticipantId) {
            tokenOwnership.set(tokenIdentifier, [ownerParticipantId]);
            console.log(`[InstanceValidator] Pre-mint: Token "${tokenIdentifier}" (${tokenInfo.tokenName}) already exists in ERC. Owner set to: ${ownerParticipantId}`);

            // Also record this as a "minted" token to prevent duplicate minting
            mintedTokens.set(tokenIdentifier, {
              taskName: '[Pre-existing in ERC]',
              taskId: 'ERC_CONTRACT',
              operation: 'mint'
            });
          } else {
            // CRITICAL: Token marked as existing but owner query failed or returned no match
            console.error(`[InstanceValidator] CRITICAL: Token "${tokenIdentifier}" (${tokenInfo.tokenName}) is marked as existing in ERC but owner could not be determined`);
            errors.push({
              taskId: 'PRE_MINT_' + tokenIdentifier,
              taskName: `Pre-existing Token: ${tokenInfo.tokenName}`,
              message: `Token "${tokenInfo.tokenName}" (ID: ${tokenIdentifier}) is marked as already existing in ERC contract (tokenHasExistInERC=true), but failed to query or determine the owner from blockchain. This could be due to:\n` +
                `1. Token does not actually exist in the ERC contract\n` +
                `2. Blockchain query failed (check network connection and ERC contract URL)\n` +
                `3. Token owner's blockchain identity (User CN) does not match any participant binding in "Binding Participants"\n` +
                `\nPlease verify the token exists on-chain and ensure the owner is correctly bound to a participant with validation type "equal".`,
              severity: 'error'
            });
          }
        })();

        preMintPromises.push(preMintTask);
      }
    });

    // Wait for all pre-mint queries to complete
    await Promise.all(preMintPromises);
    console.log('[InstanceValidator] Pre-minting completed');


    // Process tasks in execution order
    executionOrder.forEach((taskId, index) => {
      const task = taskMap.get(taskId);
      if (!task) {
        console.log(`[InstanceValidator] Task ${taskId} not found in task map, skipping`);
        return;
      }

      const taskName = task.getAttribute('name') || taskId;
      console.log(`[InstanceValidator] Processing task ${index + 1}/${executionOrder.length}: ${taskName} (${taskId})`);


      // Get task documentation (contains operation info)
      const documentation = task.querySelector('bpmn\\:documentation, documentation');
      if (!documentation) {
        console.log(`[InstanceValidator] Task ${taskName} has no documentation, skipping`);
        return;
      }

      try {
        const taskInfo = JSON.parse(documentation.textContent || '{}');
        console.log(`[InstanceValidator] Task ${taskName} info:`, taskInfo);

        const { operation, caller, callee } = taskInfo;

        if (!operation) {
          console.log(`[InstanceValidator] Task ${taskName} has no operation, skipping`);
          return;
        }

        // Get connected DataObjects for this task
        const connectedDataObjects = taskToDataObjectMap.get(taskId);
        if (!connectedDataObjects || connectedDataObjects.size === 0) {
          console.log(`[InstanceValidator] Task ${taskName} has no connected DataObjects, skipping token validation`);
          // Still validate caller binding
          if (!caller) {
            errors.push({
              taskId,
              taskName,
              message: `Operation "${operation}" requires a caller but none is specified`,
              severity: 'error'
            });
          }
          return;
        }

        console.log(`[InstanceValidator] Task ${taskName} connected to DataObjects:`, Array.from(connectedDataObjects));

        // Get the token info from taskERCMap (if available)
        const ercInfo = taskERCMap[taskId];
        console.log(`[InstanceValidator] ERC Info for task ${taskId}:`, ercInfo);

        // Get token info from the first connected DataObject that has token information
        let effectiveTokenName: string | undefined;
        let effectiveTokenId: string | undefined;
        let effectiveTokenType: string | undefined;
        let effectiveAssetType: string | undefined;
        let effectiveTokenHasExistInERC: boolean = false;
        let tokenIdentifier: string | undefined;

        for (const dataObjId of connectedDataObjects) {
          const registeredTokenEntry = Array.from(tokenTypeRegistry.entries()).find(([identifier, _info]) => {
            // Match by dataObjectId or by tokenName/tokenId
            const dataObj = xmlDoc.querySelector(`[id="${dataObjId}"]`);
            if (dataObj) {
              const documentation = dataObj.querySelector('bpmn\\:documentation, documentation');
              if (documentation) {
                try {
                  const dataObjInfo = JSON.parse(documentation.textContent || '{}');
                  return dataObjInfo.tokenName && (
                    identifier === (dataObjInfo.tokenId?.toString() || dataObjInfo.tokenName)
                  );
                } catch {
                  return false;
                }
              }
            }
            return false;
          });

          if (registeredTokenEntry) {
            const [identifier, info] = registeredTokenEntry;
            tokenIdentifier = identifier;
            effectiveTokenName = info.tokenName;
            effectiveTokenId = info.tokenId;
            effectiveTokenType = info.tokenType;
            effectiveAssetType = info.assetType;
            effectiveTokenHasExistInERC = info.tokenHasExistInERC || false;
            console.log(`[InstanceValidator] Found token from DataObject: Name=${effectiveTokenName}, ID=${effectiveTokenId}, Type=${effectiveTokenType}, AssetType=${effectiveAssetType}, HasExistInERC=${effectiveTokenHasExistInERC}`);
            break;
          }
        }

        // If no token found in registry, check if task has ERC info as fallback
        if (!tokenIdentifier && ercInfo?.tokenName) {
          effectiveTokenName = ercInfo.tokenName;
          effectiveTokenId = ercInfo.tokenId;
          tokenIdentifier = effectiveTokenId ? effectiveTokenId.toString() : effectiveTokenName;

          // Infer token type if not specified
          if (effectiveTokenId) {
            effectiveTokenType = 'NFT';
          } else {
            effectiveTokenType = 'FT';
          }
          console.log(`[InstanceValidator] Using ERC Info - Name: ${effectiveTokenName}, ID: ${effectiveTokenId}, Type: ${effectiveTokenType}`);
        }

        if (!tokenIdentifier) {
          console.log(`[InstanceValidator] Task ${taskName} has no token information, skipping token validation`);
          // Still validate caller binding
          if (!caller) {
            errors.push({
              taskId,
              taskName,
              message: `Operation "${operation}" requires a caller but none is specified`,
              severity: 'error'
            });
          }
          return;
        }

        const tokenDisplayName = effectiveTokenName
          ? (effectiveTokenId ? `${effectiveTokenName} (ID: ${effectiveTokenId})` : effectiveTokenName)
          : (effectiveTokenId || 'Unknown Token');

        console.log(`[InstanceValidator] ============================================`);
        console.log(`[InstanceValidator] Task: ${taskName} (${taskId})`);
        console.log(`[InstanceValidator] Operation: ${operation}`);
        console.log(`[InstanceValidator] Token info - Name: ${effectiveTokenName}, ID: ${effectiveTokenId}, Type: ${effectiveTokenType}, AssetType: ${effectiveAssetType}`);
        console.log(`[InstanceValidator] Token identifier: "${tokenIdentifier}"`);
        console.log(`[InstanceValidator] Caller: ${caller}`);

        // Validate ERC contract binding consistency for the same token
        if (tokenIdentifier && ercInfo) {
          const ercIdKey = Object.keys(ercInfo).find(k => k.endsWith('_ERCID'));
          const ercNameKey = Object.keys(ercInfo).find(k => k.endsWith('_ERCName'));

          const currentERCId = ercIdKey ? ercInfo[ercIdKey] : null;
          const currentERCName = ercNameKey ? ercInfo[ercNameKey] : null;

          console.log(`[InstanceValidator] ERC binding for ${tokenDisplayName} - ID: ${currentERCId}, Name: ${currentERCName}`);

          if (currentERCId && currentERCName) {
            // Check if this token was already bound to a different ERC contract
            const existingBinding = tokenERCBinding.get(tokenIdentifier);

            if (existingBinding) {
              // Same token found in another task - verify it's the same ERC contract
              if (existingBinding.ercId !== currentERCId) {
                errors.push({
                  taskId,
                  taskName,
                  message: `Token "${tokenDisplayName}" must use the same ERC contract across all operations. Task "${existingBinding.taskName}" uses "${existingBinding.ercName}" (ID: ${existingBinding.ercId}), but this task uses "${currentERCName}" (ID: ${currentERCId})`,
                  severity: 'error'
                });
              } else {
                console.log(`[InstanceValidator] ERC binding verified: ${tokenDisplayName} consistently uses ${currentERCName}`);
              }
            } else {
              // First time seeing this token - record its ERC binding
              tokenERCBinding.set(tokenIdentifier, {
                ercId: currentERCId,
                ercName: currentERCName,
                taskId,
                taskName
              });
              console.log(`[InstanceValidator] ERC binding recorded: ${tokenDisplayName} -> ${currentERCName} (first seen in ${taskName})`);
            }
          } else if (operation !== 'query') {
            // Non-query operations should have ERC binding
            errors.push({
              taskId,
              taskName,
              message: `Task "${taskName}" operating on token "${tokenDisplayName}" must be bound to an ERC contract`,
              severity: 'warning'
            });
          }
        }

        // Validate caller binding exists
        if (!caller) {
          errors.push({
            taskId,
            taskName,
            message: `Operation "${operation}" requires a caller but none is specified`,
            severity: 'error'
          });
          return;
        }

        // Find the participant binding
        const participantKey = Array.from(participantBindings.keys()).find(key =>
          key.includes(caller) || caller.includes(key)
        );

        if (!participantKey) {
          errors.push({
            taskId,
            taskName,
            message: `Caller "${caller}" is not bound to any participant`,
            severity: 'error'
          });
          return;
        }

        const binding = participantBindings.get(participantKey);

        // Check if this token has been burned (NFT only - FT can be re-minted)
        // For NFT, once burned, no further operations should be allowed except mint and query
        console.log(`[InstanceValidator] ---------- Burn Status Check ----------`);
        console.log(`[InstanceValidator] Token: ${tokenDisplayName}`);
        console.log(`[InstanceValidator] Token identifier: "${tokenIdentifier}"`);
        console.log(`[InstanceValidator] Token type: ${effectiveTokenType}`);
        console.log(`[InstanceValidator] Operation: ${operation}`);
        console.log(`[InstanceValidator] Burned tokens map keys:`, Array.from(burnedTokens.keys()));

        if (effectiveTokenType === 'NFT' && operation !== 'mint' && operation !== 'query') {
          const burnedInfo = burnedTokens.get(tokenIdentifier);
          console.log(`[InstanceValidator] Looking for burned token with identifier: "${tokenIdentifier}"`);
          console.log(`[InstanceValidator] Found burned info:`, burnedInfo);

          if (burnedInfo) {
            console.error(`[InstanceValidator] ❌❌❌ ERROR: Attempting ${operation} on burned NFT ${tokenDisplayName}`);
            errors.push({
              taskId,
              taskName,
              message: `Cannot perform "${operation}" on token "${tokenDisplayName}" because it was already burned in task "${burnedInfo.taskName}". NFT tokens cannot be used after being destroyed.`,
              severity: 'error'
            });
            return; // Skip further validation for this task
          } else {
            console.log(`[InstanceValidator] ✓ Token not burned, can proceed with ${operation}`);
          }
        } else {
          console.log(`[InstanceValidator] Skipping burn check (Type: ${effectiveTokenType}, Operation: ${operation})`);
        }

        // Validate based on operation type
        switch (operation) {
          case 'mint':
            // Mint creates new tokens - caller becomes the owner
            if (tokenIdentifier) {
              // Check if this is an NFT (not FT)
              const isNFT = effectiveTokenType !== 'FT';

              if (isNFT) {
                // Check if this token was already minted
                const previousMint = mintedTokens.get(tokenIdentifier);
                if (previousMint) {
                  errors.push({
                    taskId,
                    taskName,
                    message: `Cannot mint token "${tokenDisplayName}" because it was already minted in task "${previousMint.taskName}" with operation "${previousMint.operation}". NFT tokens can only be minted once unless they are burned first.`,
                    severity: 'error'
                  });
                  return; // Skip further processing
                }

                // Record this mint operation
                mintedTokens.set(tokenIdentifier, { taskName, taskId, operation: 'mint' });
                console.log(`[InstanceValidator] Mint: NFT ${tokenDisplayName} recorded as minted in task ${taskName}`);
              } else {
                console.log(`[InstanceValidator] Mint: FT ${tokenDisplayName} can be minted multiple times`);
              }

              tokenOwnership.set(tokenIdentifier, [caller]);
              console.log(`[InstanceValidator] Mint: ${caller} now owns ${tokenDisplayName}`);
            }

            // Validate that minter has proper authorization
            if (binding?.selectedValidationType === 'equal') {
              // Specific user binding is required for minting
              if (!binding.selectedUser) {
                errors.push({
                  taskId,
                  taskName,
                  message: `Mint operation requires a specific user binding for participant "${caller}"`,
                  severity: 'error'
                });
              }
            }
            break;

          case 'burn':
            // Burn requires ownership of the token
            if (tokenIdentifier) {
              const owners = tokenOwnership.get(tokenIdentifier) || [];
              console.log(`[InstanceValidator] Burn check: ${tokenDisplayName} (Type: ${effectiveTokenType}) owners: [${owners.join(', ')}], caller: ${caller}`);

              const hasOwnership = owners.includes(caller);

              if (!hasOwnership) {
                errors.push({
                  taskId,
                  taskName,
                  message: `Burn operation requires "${caller}" to own token "${tokenDisplayName}", but current owners are: ${owners.join(', ') || 'none'}`,
                  severity: 'error'
                });
              } else {
                // IMPORTANT: Only remove ownership and mark as burned if caller actually owns the token
                // This prevents invalid burns from corrupting the ownership state
                tokenOwnership.delete(tokenIdentifier);

                // Mark NFT as burned and remove from minted list (can be re-minted after burn)
                if (effectiveTokenType === 'NFT') {
                  burnedTokens.set(tokenIdentifier, { taskName, taskId });
                  mintedTokens.delete(tokenIdentifier); // Allow re-minting after burn
                  console.log(`[InstanceValidator] Burn: NFT ${tokenDisplayName} marked as BURNED in task ${taskName}. Token identifier: ${tokenIdentifier}`);
                  console.log(`[InstanceValidator] Burn: NFT ${tokenDisplayName} removed from minted list, can be re-minted now`);
                  console.log(`[InstanceValidator] Burned tokens map now contains:`, Array.from(burnedTokens.keys()));
                } else {
                  console.log(`[InstanceValidator] Burn: ${tokenDisplayName} (Type: ${effectiveTokenType}) removed from ownership (FT can be re-minted)`);
                }
              }
            }
            break;

          case 'transfer':
          case 'Transfer':
            // Transfer requires ownership and valid recipient
            if (tokenIdentifier) {
              const owners = tokenOwnership.get(tokenIdentifier) || [];
              console.log(`[InstanceValidator] Transfer check: ${tokenDisplayName} owners: [${owners.join(', ')}], caller: ${caller}`);

              // Check if caller owns the token
              const hasOwnership = owners.includes(caller);

              if (!hasOwnership) {
                errors.push({
                  taskId,
                  taskName,
                  message: `Transfer operation requires "${caller}" to own token "${tokenDisplayName}", but current owners are: ${owners.join(', ') || 'none'}`,
                  severity: 'error'
                });
              }

              // Validate callee exists
              if (!callee || callee.length === 0) {
                errors.push({
                  taskId,
                  taskName,
                  message: `Transfer operation requires a recipient (callee) for token "${tokenDisplayName}"`,
                  severity: 'error'
                });
              } else if (hasOwnership) {
                // IMPORTANT: Only update ownership if caller actually owns the token
                // This prevents invalid transfers from corrupting the ownership state
                tokenOwnership.set(tokenIdentifier, callee);
                console.log(`[InstanceValidator] Transfer: ${tokenDisplayName} ownership updated from [${owners.join(', ')}] to [${callee.join(', ')}]`);

                // Verify all callees are bound
                callee.forEach((calleeId: string) => {
                  const calleeKey = Array.from(participantBindings.keys()).find(key =>
                    key.includes(calleeId) || calleeId.includes(key)
                  );
                  if (!calleeKey) {
                    errors.push({
                      taskId,
                      taskName,
                      message: `Transfer recipient "${calleeId}" is not bound to any participant (token: ${tokenDisplayName})`,
                      severity: 'error'
                    });
                  }
                });
              } else {
                // Caller doesn't own the token, so we don't update ownership
                console.log(`[InstanceValidator] Transfer: Skipping ownership update because caller doesn't own the token`);
              }
            }
            break;

          case 'grant usage rights':
            // Grant usage rights requires ownership
            if (tokenIdentifier) {
              const owners = tokenOwnership.get(tokenIdentifier) || [];
              if (!owners.includes(caller)) {
                errors.push({
                  taskId,
                  taskName,
                  message: `Grant usage rights requires "${caller}" to own token "${tokenDisplayName}"`,
                  severity: 'warning'
                });
              }

              // Validate grantee exists
              if (!callee || callee.length === 0) {
                errors.push({
                  taskId,
                  taskName,
                  message: `Grant usage rights operation requires a grantee (callee) for token "${tokenDisplayName}"`,
                  severity: 'error'
                });
              }
            }
            break;

          case 'revoke usage rights':
            // Revoke usage rights requires ownership
            if (tokenIdentifier) {
              const owners = tokenOwnership.get(tokenIdentifier) || [];
              if (!owners.includes(caller)) {
                errors.push({
                  taskId,
                  taskName,
                  message: `Revoke usage rights requires "${caller}" to own token "${tokenDisplayName}"`,
                  severity: 'warning'
                });
              }
            }
            break;

          case 'branch':
          case 'merge':
            // Branch/merge operations for value-added tokens - these are equivalent to minting
            if (effectiveAssetType === 'value-added') {
              if (tokenIdentifier) {
                // Check if this token was already minted/branched/merged
                const previousMint = mintedTokens.get(tokenIdentifier);
                if (previousMint) {
                  errors.push({
                    taskId,
                    taskName,
                    message: `Cannot ${operation} token "${tokenDisplayName}" because it was already created in task "${previousMint.taskName}" with operation "${previousMint.operation}". Value-added tokens can only be created once unless they are burned first.`,
                    severity: 'error'
                  });
                  return; // Skip further processing
                }

                // Record this branch/merge as a mint-equivalent operation
                mintedTokens.set(tokenIdentifier, { taskName, taskId, operation });
                console.log(`[InstanceValidator] ${operation}: Value-added token ${tokenDisplayName} recorded as created in task ${taskName}`);

                // For branch/merge, caller should own the source token (if checking ownership)
                const owners = tokenOwnership.get(tokenIdentifier) || [];
                if (owners.length > 0 && !owners.includes(caller)) {
                  errors.push({
                    taskId,
                    taskName,
                    message: `${operation} operation requires "${caller}" to own token "${tokenDisplayName}"`,
                    severity: 'warning'
                  });
                }

                // After branch/merge, caller owns the new token
                tokenOwnership.set(tokenIdentifier, [caller]);
                console.log(`[InstanceValidator] ${operation}: ${caller} now owns ${tokenDisplayName}`);
              }
            }
            break;

          case 'query':
            // Query operations are open to all participants
            // No ownership requirements - anyone can query token information
            // Query does not modify token ownership or state
            console.log(`[InstanceValidator] Query operation: ${caller} querying ${tokenDisplayName} (no ownership check)`);
            break;

          default:
            errors.push({
              taskId,
              taskName,
              message: `Unknown operation type: "${operation}"`,
              severity: 'warning'
            });
        }

        // Additional validation for FT tokens
        if (effectiveAssetType === 'transferable' && effectiveTokenType === 'FT') {
          if (operation !== 'query' && !taskInfo.tokenNumber) {
            errors.push({
              taskId,
              taskName,
              message: `FT token operation requires tokenNumber to be specified`,
              severity: 'warning'
            });
          }
        }

      } catch (parseError) {
        // Ignore tasks without valid documentation
      }
    });

  } catch (error) {
    console.error('[InstanceValidator] Validation error:', error);
    console.error('[InstanceValidator] Error stack:', error?.stack);
    errors.push({
      taskId: 'GLOBAL',
      taskName: 'Validation',
      message: `Failed to validate instance: ${error.message}`,
      severity: 'error'
    });
  }

  const finalResult = {
    isValid: errors.filter(e => e.severity === 'error').length === 0,
    errors
  };

  console.log('[InstanceValidator] Validation complete. Result:', finalResult);
  return finalResult;
}

/**
 * Find participant ID by blockchain identity
 * This function queries the blockchain to get the token owner and matches it with participant bindings
 *
 * @param participantBindings - Map of participant bindings
 * @param tokenIdentifier - The token identifier to query
 * @param tokenInfo - Token information including type and chaincode name
 * @param ercChaincodeUrl - The ERC chaincode URL for querying
 * @returns The participant ID that matches the blockchain identity, or null if not found
 */
async function findParticipantByBlockchainIdentity(
  participantBindings: Map<string, ParticipantBinding>,
  tokenIdentifier: string,
  tokenInfo: { tokenType: string; assetType?: string; tokenName: string },
  ercChaincodeUrl: string | null
): Promise<string | null> {
  console.log(`[findParticipantByBlockchainIdentity] Querying owner for token "${tokenIdentifier}"`);
  console.log(`[findParticipantByBlockchainIdentity] Token info:`, tokenInfo);
  console.log(`[findParticipantByBlockchainIdentity] ERC chaincode URL:`, ercChaincodeUrl);

  if (!ercChaincodeUrl) {
    console.warn(`[findParticipantByBlockchainIdentity] No ERC chaincode URL provided for token "${tokenIdentifier}"`);
    return null;
  }

  try {
    // Step 1: Query blockchain for token owner using OwnerOf
    const blockchainOwnerIdentity = await queryTokenOwnerFromBlockchain(
      ercChaincodeUrl,
      tokenIdentifier,
      tokenInfo
    );

    if (!blockchainOwnerIdentity) {
      console.warn(`[findParticipantByBlockchainIdentity] No owner found for token "${tokenIdentifier}"`);
      return null;
    }

    console.log(`[findParticipantByBlockchainIdentity] Blockchain owner identity:`, blockchainOwnerIdentity);

    // Step 2: Parse the blockchain identity
    const { mspId, userCN } = parseBlockchainIdentity(blockchainOwnerIdentity);
    console.log(`[findParticipantByBlockchainIdentity] Parsed identity - MSP: ${mspId}, User CN: ${userCN}`);

    // Step 3: Match with participant bindings
    for (const [participantId, binding] of participantBindings.entries()) {
      console.log(`[findParticipantByBlockchainIdentity] Checking participant "${participantId}":`, {
        validationType: binding.selectedValidationType,
        membershipId: binding.selectedMembershipId,
        user: binding.selectedUser
      });

      // Match logic:
      // 1. Must be 'equal' validation type (specific user binding)
      // 2. selectedMembershipId should match MSP ID (if available)
      // 3. selectedUser should match user CN
      if (binding.selectedValidationType === 'equal') {
        // Note: selectedMembershipId is the membership resource ID, we need to compare the MSP
        // For now, we'll match based on user CN primarily
        // TODO: Enhance this to also verify MSP matching if needed

        if (binding.selectedUser === userCN) {
          console.log(`[findParticipantByBlockchainIdentity] ✓ Matched participant "${participantId}" for token "${tokenIdentifier}"`);
          return participantId;
        }
      }
    }

    console.warn(`[findParticipantByBlockchainIdentity] No matching participant found for identity: ${blockchainOwnerIdentity}`);
    console.log(`[findParticipantByBlockchainIdentity] Available participant bindings:`,
      Array.from(participantBindings.entries()).map(([id, binding]) => ({
        participantId: id,
        validationType: binding.selectedValidationType,
        membershipId: binding.selectedMembershipId,
        user: binding.selectedUser,
        attrs: binding.Attr
      }))
    );

    return null;
  } catch (error) {
    console.error(`[findParticipantByBlockchainIdentity] Error querying token owner:`, error);
    return null;
  }
}

/**
 * Query token owner from blockchain using OwnerOf chaincode method
 * Supports ERC721 (transferable NFT), ERC5521 (distributive), and ERC5521 (value-added)
 *
 * @param ercChaincodeUrl - The ERC chaincode URL
 * @param tokenId - The token ID to query
 * @param tokenInfo - Token information including type and asset type
 * @returns The owner identity in format: "MSP::x509::CN=user,OU=client::..."
 */
async function queryTokenOwnerFromBlockchain(
  ercChaincodeUrl: string,
  tokenId: string,
  tokenInfo: { tokenType: string; assetType?: string; tokenName: string }
): Promise<string | null> {
  console.log(`[queryTokenOwnerFromBlockchain] Querying owner for token "${tokenId}"`);
  console.log(`[queryTokenOwnerFromBlockchain] Asset type: ${tokenInfo.assetType}, Token type: ${tokenInfo.tokenType}`);

  try {
    // Import fireflyAPI dynamically
    const { fireflyAPI } = await import('@/api/apiConfig.ts');

    // Determine which contract method to call based on token type
    // ERC721 (transferable NFT) -> OwnerOf
    // ERC5521 (distributive) -> OwnerOf
    // ERC5521 (value-added) -> OwnerOf
    // All three use the same OwnerOf method signature

    const methodName = 'OwnerOf';

    // Construct the API URL
    // Format: {ercChaincodeUrl}/query/OwnerOf
    const apiUrl = `${ercChaincodeUrl.replace(/\/+$/, '')}/query/${methodName}`;

    console.log(`[queryTokenOwnerFromBlockchain] Calling ${apiUrl} with tokenId: ${tokenId}`);

    // Call the chaincode query method
    const response = await fireflyAPI.post(apiUrl, {
      input: {
        tokenId: tokenId
      }
    });

    console.log(`[queryTokenOwnerFromBlockchain] Response:`, response.data);

    // Extract the owner identity from response
    // Expected response format: { output: "MSP::x509::CN=user,OU=client::..." }
    const ownerIdentity = response.data?.output;

    if (!ownerIdentity) {
      console.warn(`[queryTokenOwnerFromBlockchain] No owner identity in response for token "${tokenId}"`);
      return null;
    }

    console.log(`[queryTokenOwnerFromBlockchain] Successfully retrieved owner: ${ownerIdentity}`);
    return ownerIdentity;

  } catch (error: any) {
    console.error(`[queryTokenOwnerFromBlockchain] Error querying blockchain:`, error);
    console.error(`[queryTokenOwnerFromBlockchain] Error details:`, error.response?.data || error.message);
    return null;
  }
}

/**
 * Parse blockchain identity string to extract MSP ID and user CN
 *
 * @param identity - Identity string in format: "MSP::x509::CN=user,OU=client::..."
 * @returns Parsed identity with mspId and userCN
 *
 * Example input: "Mem.org.comMSP::x509::CN=user1,OU=client::CN=ca.mem.org.com,OU=Fabric,O=mem.org.com,ST=North Carolina,C=US"
 * Example output: { mspId: "Mem.org.comMSP", userCN: "user1" }
 */
function parseBlockchainIdentity(identity: string): { mspId: string; userCN: string } {
  console.log(`[parseBlockchainIdentity] Parsing identity: ${identity}`);

  try {
    // Split by "::" to get parts
    const parts = identity.split('::');

    if (parts.length < 3) {
      console.warn(`[parseBlockchainIdentity] Invalid identity format: ${identity}`);
      return { mspId: '', userCN: '' };
    }

    // Part 0: MSP ID (e.g., "Mem.org.comMSP")
    const mspId = parts[0];

    // Part 2: X509 DN string (e.g., "CN=user1,OU=client")
    const x509Part = parts[2];

    // Extract CN (Common Name) from the X509 DN
    const cnMatch = x509Part.match(/CN=([^,]+)/);
    const userCN = cnMatch ? cnMatch[1] : '';

    console.log(`[parseBlockchainIdentity] Parsed - MSP: "${mspId}", User CN: "${userCN}"`);

    return { mspId, userCN };
  } catch (error) {
    console.error(`[parseBlockchainIdentity] Error parsing identity:`, error);
    return { mspId: '', userCN: '' };
  }
}

/**
 * Format validation errors for display
 */
export function formatValidationErrors(errors: ValidationError[]): string {
  if (errors.length === 0) {
    return 'No validation errors found. All token operations and participant bindings are valid.';
  }

  const errorCount = errors.filter(e => e.severity === 'error').length;
  const warningCount = errors.filter(e => e.severity === 'warning').length;

  let output = `Found ${errorCount} error(s) and ${warningCount} warning(s):\n\n`;

  errors.forEach((error, index) => {
    const icon = error.severity === 'error' ? '❌' : '⚠️';
    output += `${index + 1}. ${icon} [${error.taskName}] ${error.message}\n`;
  });

  return output;
}
