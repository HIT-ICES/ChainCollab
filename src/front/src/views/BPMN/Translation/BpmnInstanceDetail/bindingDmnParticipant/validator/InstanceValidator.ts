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

    // Use BPMN's Firefly URL directly (same as ERCAddMintAuthority uses)
    // This ensures we query the same Firefly instance as the BPMN instance
    console.log('[InstanceValidator] BPMN Firefly URL (from bpmn.firefly_url):', bpmnFireflyUrl);

    tokenTypeRegistry.forEach((tokenInfo, tokenIdentifier) => {
      if (tokenInfo.tokenHasExistInERC) {
        const preMintTask = (async () => {
          // Find the ERC chaincode name and construct URL with registered API name
          // IMPORTANT: Use BPMN's Firefly URL, not ERC's own Firefly URL
          let ercChaincodeUrl: string | null = null;
          let ercChaincodeName: string | null = null;

          for (const [_, ercInfo] of Object.entries(taskERCMap)) {
            // Check if this task uses the current token
            if (ercInfo.tokenName === tokenInfo.tokenName) {
              // Extract ERC ID to get the chaincode name
              const ercIdKey = Object.keys(ercInfo).find(k => k.endsWith('_ERCID'));
              const ercId = ercIdKey ? ercInfo[ercIdKey] : null;

              if (ercId) {
                try {
                  // Import API functions dynamically
                  const { retrieveERCChaincode } = await import('@/api/externalResource');
                  const { fireflyAPI } = await import('@/api/apiConfig.ts');

                  // Query ERC chaincode info to get the chaincode name
                  const erc = await retrieveERCChaincode(ercId);

                  if (erc && erc.name) {
                    ercChaincodeName = erc.name;
                    console.log(`[InstanceValidator] Retrieved ERC chaincode name for token ${tokenIdentifier}: ${ercChaincodeName}`);

                    // CRITICAL: Use BPMN's Firefly URL and increment port by 1 for ERC queries
                    // This is a workaround where ERC contracts are deployed on port+1
                    if (bpmnFireflyUrl) {
                      try {
                        // Extract base URL and port from bpmnFireflyUrl
                        // Input: http://127.0.0.1:5002/api/v1/namespaces/default/apis/test9-bdccb7
                        const urlMatch = bpmnFireflyUrl.match(/^(https?:\/\/[^:]+):(\d+)(\/api\/v1\/namespaces\/[^\/]+\/apis)/);

                        if (!urlMatch) {
                          console.warn(`[InstanceValidator] Could not parse bpmnFireflyUrl: ${bpmnFireflyUrl}`);
                          ercChaincodeUrl = bpmnFireflyUrl; // Use as-is
                        } else {
                          const protocol = urlMatch[1]; // http://127.0.0.1
                          const port = parseInt(urlMatch[2], 10); // 5000
                          const pathPrefix = urlMatch[3]; // /api/v1/namespaces/default/apis

                          // Increment port by 1 for ERC queries
                          const ercPort = port + 1; // 5000 -> 5001
                          const baseApisUrl = `${protocol}:${ercPort}${pathPrefix}`;

                          console.log(`[InstanceValidator] Original port: ${port}, ERC port: ${ercPort}`);
                          console.log(`[InstanceValidator] Querying API list from: ${baseApisUrl}`);

                          const apisResponse = await fireflyAPI.get(baseApisUrl);
                          const apisList = apisResponse.data;

                          if (Array.isArray(apisList)) {
                            // Find the registered API name for this chaincode
                            const matchingApi = apisList.find((api: any) =>
                              api.location && api.location.chaincode === ercChaincodeName
                            );

                            if (matchingApi) {
                              // Use the registered API name (e.g., "ERC721test1-5e139d")
                              ercChaincodeUrl = `${baseApisUrl}/${matchingApi.name}`;
                              console.log(`[InstanceValidator] ✓ Found registered API name: ${matchingApi.name}`);
                              console.log(`[InstanceValidator] ✓ Constructed URL: ${ercChaincodeUrl}`);
                            } else {
                              // Fallback: use chaincode name directly
                              ercChaincodeUrl = `${baseApisUrl}/${ercChaincodeName}`;
                              console.warn(`[InstanceValidator] ⚠ No registered API found for chaincode ${ercChaincodeName}, using chaincode name directly`);
                            }
                          } else {
                            ercChaincodeUrl = `${baseApisUrl}/${ercChaincodeName}`;
                            console.warn(`[InstanceValidator] Unexpected API list response, using chaincode name directly`);
                          }
                        }
                      } catch (apiListError) {
                        console.error(`[InstanceValidator] Failed to query API list:`, apiListError);
                        // Fallback: use bpmnFireflyUrl as base and append chaincode name
                        const baseUrl = bpmnFireflyUrl.substring(0, bpmnFireflyUrl.lastIndexOf('/'));
                        ercChaincodeUrl = `${baseUrl}/${ercChaincodeName}`;
                        console.log(`[InstanceValidator] Fallback - using chaincode name: ${ercChaincodeUrl}`);
                      }
                    } else {
                      console.warn(`[InstanceValidator] No BPMN Firefly URL available`);
                    }
                  } else {
                    console.warn(`[InstanceValidator] ERC ${ercId} has no name`);
                    // Fallback: try to get name from ercInfo
                    const ercNameKey = Object.keys(ercInfo).find(k => k.endsWith('_ERCName'));
                    if (ercNameKey && bpmnFireflyUrl) {
                      ercChaincodeName = ercInfo[ercNameKey];
                      const baseUrl = bpmnFireflyUrl.substring(0, bpmnFireflyUrl.lastIndexOf('/'));
                      ercChaincodeUrl = `${baseUrl}/${ercChaincodeName}`;
                      console.log(`[InstanceValidator] Fallback - Using ERC name from ercInfo: ${ercChaincodeUrl}`);
                    }
                  }
                } catch (err) {
                  console.error(`[InstanceValidator] Error retrieving ERC ${ercId}:`, err);
                  // Fallback: construct from ERC name in ercInfo
                  const ercNameKey = Object.keys(ercInfo).find(k => k.endsWith('_ERCName'));
                  if (ercNameKey && bpmnFireflyUrl) {
                    ercChaincodeName = ercInfo[ercNameKey];
                    const baseUrl = bpmnFireflyUrl.substring(0, bpmnFireflyUrl.lastIndexOf('/'));
                    ercChaincodeUrl = `${baseUrl}/${ercChaincodeName}`;
                    console.log(`[InstanceValidator] Exception fallback - Constructed URL: ${ercChaincodeUrl}`);
                  }
                }
              } else {
                console.warn(`[InstanceValidator] No ERC ID found for token ${tokenIdentifier}`);
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

          // ===== Query blockchain for owner based on asset type =====
          // Branch 1: FT (Fungible Token) - No tokenId, query balance for all participants
          // Branch 2: Transferable NFT + Value-added - Use OwnerOf query
          // Branch 3: Distributive - Use different query method

          let ownerParticipantId: string | null = null;

          if (tokenInfo.tokenType === 'FT') {
            // Branch 1: FT - Query balance for each participant to find who owns it
            console.log(`[InstanceValidator] Pre-mint: FT token "${tokenInfo.tokenName}" - querying balance for all participants`);
            ownerParticipantId = await findParticipantByFTBalance(
              participantBindings,
              tokenInfo.tokenName,
              ercChaincodeUrl
            );
          } else if (tokenInfo.assetType === 'transferable' || tokenInfo.assetType === 'value-added') {
            // Branch 2: Transferable NFT or Value-added - Use OwnerOf query
            console.log(`[InstanceValidator] Pre-mint: ${tokenInfo.assetType} token "${tokenIdentifier}" - querying OwnerOf`);
            ownerParticipantId = await findParticipantByBlockchainIdentity(
              participantBindings,
              tokenIdentifier,
              tokenInfo,
              ercChaincodeUrl
            );
          } else if (tokenInfo.assetType === 'distributive') {
            // Branch 3: Distributive - Query owner and users
            console.log(`[InstanceValidator] Pre-mint: Distributive token "${tokenIdentifier}" - querying owner and users`);
            ownerParticipantId = await findParticipantForDistributive(
              participantBindings,
              tokenIdentifier,
              tokenInfo,
              ercChaincodeUrl
            );
          } else {
            console.warn(`[InstanceValidator] Unknown asset type "${tokenInfo.assetType}" for token "${tokenIdentifier}"`);
          }

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

            let errorMessage = `Token "${tokenInfo.tokenName}" (ID: ${tokenIdentifier}) is marked as already existing in ERC contract (tokenHasExistInERC=true), but failed to query or determine the owner from blockchain. This could be due to:\n`;

            if (tokenInfo.tokenType === 'FT') {
              errorMessage += `1. Token does not actually exist in the ERC contract\n` +
                `2. Blockchain query failed (check network connection and ERC contract URL)\n` +
                `3. No participant has a non-zero balance of this FT token\n` +
                `\nPlease verify the token exists on-chain and ensure at least one participant is bound with validation type "equal" and has a balance > 0.`;
            } else if (tokenInfo.assetType === 'distributive') {
              errorMessage += `1. Token does not actually exist in the ERC contract\n` +
                `2. Blockchain query failed (check network connection and ERC contract URL)\n` +
                `3. Token owner's blockchain identity (User CN) does not match any participant binding in "Binding Participants"\n` +
                `\nPlease verify the token exists on-chain and ensure the owner is correctly bound to a participant with validation type "equal".`;
            } else {
              errorMessage += `1. Token does not actually exist in the ERC contract\n` +
                `2. Blockchain query failed (check network connection and ERC contract URL)\n` +
                `3. Token owner's blockchain identity (User CN) does not match any participant binding in "Binding Participants"\n` +
                `\nPlease verify the token exists on-chain and ensure the owner is correctly bound to a participant with validation type "equal".`;
            }

            errors.push({
              taskId: 'PRE_MINT_' + tokenIdentifier,
              taskName: `Pre-existing Token: ${tokenInfo.tokenName}`,
              message: errorMessage,
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
    // The blockchain query returns identity without MSP prefix: "x509::CN=user3..."
    // The participant binding stores x509 in base64 encoded format with @MSP suffix
    // Format: "base64EncodedX509@MSP" where base64 decodes to "x509::CN=user3..."
    console.log(`[findParticipantByBlockchainIdentity] ========== Starting Participant Matching ==========`);
    console.log(`[findParticipantByBlockchainIdentity] Target blockchain identity: "${blockchainOwnerIdentity}"`);
    console.log(`[findParticipantByBlockchainIdentity] Parsed MSP ID: "${mspId}"`);
    console.log(`[findParticipantByBlockchainIdentity] Parsed User CN: "${userCN}"`);
    console.log(`[findParticipantByBlockchainIdentity] Total participant bindings to check: ${participantBindings.size}`);

    let matchAttemptCount = 0;

    for (const [participantId, binding] of participantBindings.entries()) {
      matchAttemptCount++;
      console.log(`[findParticipantByBlockchainIdentity] ========== Attempt ${matchAttemptCount}/${participantBindings.size} ==========`);
      console.log(`[findParticipantByBlockchainIdentity] Checking participant: "${participantId}"`);
      console.log(`[findParticipantByBlockchainIdentity] Binding details:`, {
        validationType: binding.selectedValidationType,
        membershipId: binding.selectedMembershipId,
        selectedUser: binding.selectedUser,
        hasAttr: binding.Attr ? true : false,
        attrCount: binding.Attr ? binding.Attr.length : 0
      });

      // Match logic:
      // 1. Must be 'equal' validation type (specific user binding)
      // 2. Extract and decode x509 from binding, then compare with blockchain identity
      if (binding.selectedValidationType === 'equal') {
        console.log(`[findParticipantByBlockchainIdentity] ✓ Validation type is 'equal', proceeding with matching...`);

        // Try to match by user CN (backward compatibility)
        console.log(`[findParticipantByBlockchainIdentity] [Match Method 1] Trying to match by selectedUser CN...`);
        console.log(`[findParticipantByBlockchainIdentity] Comparing: selectedUser="${binding.selectedUser}" vs userCN="${userCN}"`);
        if (binding.selectedUser === userCN) {
          console.log(`[findParticipantByBlockchainIdentity] ✓✓✓ MATCHED! Participant "${participantId}" matched by user CN "${userCN}"`);
          return participantId;
        } else {
          console.log(`[findParticipantByBlockchainIdentity] ✗ No match with selectedUser`);
        }

        // Also try to match if selectedUser is in format "user@MSP" or just "user"
        if (binding.selectedUser) {
          console.log(`[findParticipantByBlockchainIdentity] [Match Method 2] Trying to match by extracting username from selectedUser...`);
          const selectedUserParts = binding.selectedUser.split('@');
          const selectedUserName = selectedUserParts[0];
          console.log(`[findParticipantByBlockchainIdentity] Extracted username: "${selectedUserName}" (from "${binding.selectedUser}")`);
          console.log(`[findParticipantByBlockchainIdentity] Comparing: selectedUserName="${selectedUserName}" vs userCN="${userCN}"`);

          if (selectedUserName === userCN) {
            console.log(`[findParticipantByBlockchainIdentity] ✓✓✓ MATCHED! Participant "${participantId}" matched by username part "${userCN}"`);
            return participantId;
          } else {
            console.log(`[findParticipantByBlockchainIdentity] ✗ No match with extracted username`);
          }
        }

        // NEW: Try to match by decoding x509 field from binding attributes
        // The binding might have additional attributes with x509 encoded identity
        console.log(`[findParticipantByBlockchainIdentity] [Match Method 3] Trying to match by decoding x509 from binding attributes...`);
        if (binding.Attr && Array.isArray(binding.Attr)) {
          console.log(`[findParticipantByBlockchainIdentity] Found ${binding.Attr.length} attributes in binding`);

          for (let i = 0; i < binding.Attr.length; i++) {
            const attr = binding.Attr[i];
            console.log(`[findParticipantByBlockchainIdentity] Checking attribute ${i + 1}/${binding.Attr.length}:`, {
              attrName: attr.attr,
              valuePreview: attr.value ? `${attr.value.substring(0, 50)}...` : 'null'
            });

            if (attr.attr === 'x509' && attr.value) {
              console.log(`[findParticipantByBlockchainIdentity] ✓ Found x509 attribute with value`);
              console.log(`[findParticipantByBlockchainIdentity] Raw x509 value: "${attr.value}"`);

              try {
                // Extract base64 part (before @MSP)
                const parts = attr.value.split('@');
                const x509Value = parts[0];
                const mspPart = parts[1] || 'no-msp';
                console.log(`[findParticipantByBlockchainIdentity] Split x509 value by '@':`);
                console.log(`[findParticipantByBlockchainIdentity]   - Base64 part (before @): "${x509Value.substring(0, 50)}..."`);
                console.log(`[findParticipantByBlockchainIdentity]   - MSP part (after @): "${mspPart}"`);

                // Decode from base64
                console.log(`[findParticipantByBlockchainIdentity] Attempting base64 decode...`);
                const decodedX509 = atob(x509Value);
                console.log(`[findParticipantByBlockchainIdentity] ✓ Successfully decoded base64`);
                console.log(`[findParticipantByBlockchainIdentity] Decoded x509 identity: "${decodedX509}"`);
                console.log(`[findParticipantByBlockchainIdentity] Target blockchain identity: "${blockchainOwnerIdentity}"`);
                console.log(`[findParticipantByBlockchainIdentity] Comparison:`);
                console.log(`[findParticipantByBlockchainIdentity]   Decoded Length: ${decodedX509.length}`);
                console.log(`[findParticipantByBlockchainIdentity]   Target Length: ${blockchainOwnerIdentity.length}`);
                console.log(`[findParticipantByBlockchainIdentity]   Are they equal? ${decodedX509 === blockchainOwnerIdentity}`);

                // Compare decoded x509 with blockchain identity
                if (decodedX509 === blockchainOwnerIdentity) {
                  console.log(`[findParticipantByBlockchainIdentity] ✓✓✓ MATCHED! Participant "${participantId}" matched by x509 identity`);
                  return participantId;
                } else {
                  console.log(`[findParticipantByBlockchainIdentity] ✗ Decoded x509 does NOT match blockchain identity`);
                  // Show character-by-character comparison for first 100 chars if different
                  if (decodedX509.length < 200 && blockchainOwnerIdentity.length < 200) {
                    console.log(`[findParticipantByBlockchainIdentity] Character comparison (first 100 chars):`);
                    const maxLen = Math.min(100, Math.max(decodedX509.length, blockchainOwnerIdentity.length));
                    for (let j = 0; j < maxLen; j++) {
                      const c1 = decodedX509[j] || '(end)';
                      const c2 = blockchainOwnerIdentity[j] || '(end)';
                      if (c1 !== c2) {
                        console.log(`[findParticipantByBlockchainIdentity]   Position ${j}: decoded='${c1}' vs target='${c2}' [DIFF]`);
                      }
                    }
                  }
                }
              } catch (decodeError) {
                console.error(`[findParticipantByBlockchainIdentity] ✗✗✗ Failed to decode x509 for participant "${participantId}":`, decodeError);
                console.error(`[findParticipantByBlockchainIdentity] Error details:`, {
                  errorMessage: decodeError.message,
                  errorStack: decodeError.stack
                });
              }
            } else {
              console.log(`[findParticipantByBlockchainIdentity] Skipping attribute (not x509 or no value)`);
            }
          }
        } else {
          console.log(`[findParticipantByBlockchainIdentity] ✗ No Attr array found in binding or Attr is empty`);
        }

        console.log(`[findParticipantByBlockchainIdentity] ✗ All matching methods failed for participant "${participantId}"`);
      } else {
        console.log(`[findParticipantByBlockchainIdentity] ✗ Skipping participant (validation type is not 'equal', it's '${binding.selectedValidationType}')`);
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

    // Extract components from ercChaincodeUrl
    // ercChaincodeUrl format: http://host:port/api/v1/namespaces/default/apis/{ercName}
    console.log(`[queryTokenOwnerFromBlockchain] ERC Chaincode URL: ${ercChaincodeUrl}`);

    // Parse the URL to extract base API URL
    // ercChaincodeUrl format: http://127.0.0.1:5002/api/v1/namespaces/default/apis/test9-bdccb7
    // We need to extract: http://127.0.0.1:5002/api/v1/namespaces/default/apis
    const urlMatch = ercChaincodeUrl.match(/^(https?:\/\/[^\/]+\/api\/v1\/namespaces\/[^\/]+\/apis)\/(.+)$/);

    if (!urlMatch) {
      console.error(`[queryTokenOwnerFromBlockchain] Invalid ERC chaincode URL format: ${ercChaincodeUrl}`);
      return null;
    }

    const baseApisUrl = urlMatch[1]; // http://127.0.0.1:5002/api/v1/namespaces/default/apis
    const currentRegisteredName = urlMatch[2]; // test9-bdccb7 (current registered API name)

    console.log(`[queryTokenOwnerFromBlockchain] Base APIs URL: ${baseApisUrl}`);
    console.log(`[queryTokenOwnerFromBlockchain] Current registered API name: ${currentRegisteredName}`);

    // Query Firefly to get the list of registered APIs
    console.log(`[queryTokenOwnerFromBlockchain] Querying Firefly APIs: ${baseApisUrl}`);

    let registeredApiName = currentRegisteredName; // Default to current registered name
    let ercChaincodeName = ''; // Will be extracted from API list

    try {
      const apisResponse = await fireflyAPI.get(baseApisUrl);
      const apisList = apisResponse.data;

      console.log(`[queryTokenOwnerFromBlockchain] Firefly APIs response (${Array.isArray(apisList) ? apisList.length : 0} items):`, apisList);

      if (Array.isArray(apisList) && apisList.length > 0) {
        console.log(`[queryTokenOwnerFromBlockchain] Found ${apisList.length} registered APIs`);

        // Find the API with the current registered name to get the actual chaincode name
        const currentApi = apisList.find((api: any) => api.name === currentRegisteredName);

        if (currentApi && currentApi.location && currentApi.location.chaincode) {
          ercChaincodeName = currentApi.location.chaincode;
          console.log(`[queryTokenOwnerFromBlockchain] ✓ Found API with name "${currentRegisteredName}"`);
          console.log(`[queryTokenOwnerFromBlockchain] ✓ Extracted chaincode name: ${ercChaincodeName}`);
          console.log(`[queryTokenOwnerFromBlockchain] ✓ API details:`, {
            id: currentApi.id,
            name: currentApi.name,
            chaincode: currentApi.location.chaincode,
            channel: currentApi.location.channel,
            urls: currentApi.urls
          });
        } else {
          console.warn(`[queryTokenOwnerFromBlockchain] ⚠ No API found with registered name: ${currentRegisteredName}`);
          console.log(`[queryTokenOwnerFromBlockchain] Available API names:`,
            apisList.map((a: any) => a.name).filter(Boolean)
          );
        }
      } else {
        console.warn(`[queryTokenOwnerFromBlockchain] Unexpected API response format or empty list:`, apisList);
      }
    } catch (listError: any) {
      console.warn(`[queryTokenOwnerFromBlockchain] Failed to query Firefly APIs:`, listError.message);
      console.warn(`[queryTokenOwnerFromBlockchain] Will try with current registered name: ${currentRegisteredName}`);
    }

    // Construct the query URL using the registered API name
    // Format: {baseApisUrl}/{registeredApiName}/query/OwnerOf
    const queryUrl = `${baseApisUrl}/${registeredApiName}/query/OwnerOf`;

    console.log(`[queryTokenOwnerFromBlockchain] Query URL: ${queryUrl}`);
    console.log(`[queryTokenOwnerFromBlockchain] Querying OwnerOf for tokenId: ${tokenId}`);

    // Call the Firefly registered API query method
    const response = await fireflyAPI.post(queryUrl, {
      input: {
        tokenId: tokenId
      }
    });

    console.log(`[queryTokenOwnerFromBlockchain] ========== Response Analysis ==========`);
    console.log(`[queryTokenOwnerFromBlockchain] Full response object:`, response);
    console.log(`[queryTokenOwnerFromBlockchain] response.data type:`, typeof response.data);
    console.log(`[queryTokenOwnerFromBlockchain] response.data value:`, response.data);

    // Extract the owner identity from response
    // The response format may vary:
    // Format 1: { output: "x509::CN=user..." }
    // Format 2: "x509::CN=user..." (direct string)
    // Format 3: { data: "x509::CN=user..." } or similar nested structure
    let ownerIdentity: string | null = null;

    console.log(`[queryTokenOwnerFromBlockchain] Attempting to extract owner identity...`);

    // Try Format 1: response.data.output
    if (response.data?.output) {
      ownerIdentity = response.data.output;
      console.log(`[queryTokenOwnerFromBlockchain] ✓ Found owner in response.data.output: "${ownerIdentity}"`);
    }
    // Try Format 2: response.data is the identity string directly
    else if (typeof response.data === 'string' && response.data.includes('x509')) {
      ownerIdentity = response.data;
      console.log(`[queryTokenOwnerFromBlockchain] ✓ Found owner as direct string in response.data: "${ownerIdentity}"`);
    }
    // Try Format 3: check other common field names
    else if (response.data?.result) {
      ownerIdentity = response.data.result;
      console.log(`[queryTokenOwnerFromBlockchain] ✓ Found owner in response.data.result: "${ownerIdentity}"`);
    }
    else if (response.data?.owner) {
      ownerIdentity = response.data.owner;
      console.log(`[queryTokenOwnerFromBlockchain] ✓ Found owner in response.data.owner: "${ownerIdentity}"`);
    }
    else if (response.data?.value) {
      ownerIdentity = response.data.value;
      console.log(`[queryTokenOwnerFromBlockchain] ✓ Found owner in response.data.value: "${ownerIdentity}"`);
    }
    else {
      console.error(`[queryTokenOwnerFromBlockchain] ✗ Could not extract owner identity from response`);
      console.error(`[queryTokenOwnerFromBlockchain] Available fields in response.data:`, Object.keys(response.data || {}));
      console.error(`[queryTokenOwnerFromBlockchain] Full response.data:`, JSON.stringify(response.data, null, 2));
    }

    if (!ownerIdentity) {
      console.warn(`[queryTokenOwnerFromBlockchain] No owner identity in response for token "${tokenId}"`);
      console.warn(`[queryTokenOwnerFromBlockchain] This could mean:`);
      console.warn(`[queryTokenOwnerFromBlockchain]   1. Token does not exist in the ERC contract`);
      console.warn(`[queryTokenOwnerFromBlockchain]   2. Response format is unexpected`);
      console.warn(`[queryTokenOwnerFromBlockchain]   3. OwnerOf query failed or returned empty`);
      return null;
    }

    console.log(`[queryTokenOwnerFromBlockchain] ========== Success ==========`);
    console.log(`[queryTokenOwnerFromBlockchain] Successfully retrieved owner: "${ownerIdentity}"`);
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
 * @param identity - Identity string in one of these formats:
 *   1. "MSP::x509::CN=user,OU=client::..." (with MSP prefix)
 *   2. "x509::CN=user,OU=client::..." (without MSP prefix - actual NFT query format)
 * @returns Parsed identity with mspId and userCN
 *
 * Example input 1: "Mem.org.comMSP::x509::CN=user1,OU=client::CN=ca.mem.org.com,OU=Fabric,O=mem.org.com,ST=North Carolina,C=US"
 * Example output 1: { mspId: "Mem.org.comMSP", userCN: "user1" }
 *
 * Example input 2: "x509::CN=user3,OU=client::CN=ca.mem.org.com,OU=Fabric,O=mem.org.com,ST=North Carolina,C=US"
 * Example output 2: { mspId: "", userCN: "user3" }
 */
function parseBlockchainIdentity(identity: string): { mspId: string; userCN: string } {
  console.log(`[parseBlockchainIdentity] ========== Starting Identity Parsing ==========`);
  console.log(`[parseBlockchainIdentity] Input identity: "${identity}"`);
  console.log(`[parseBlockchainIdentity] Identity length: ${identity.length}`);

  try {
    // Split by "::" to get parts
    console.log(`[parseBlockchainIdentity] Splitting identity by "::"...`);
    const parts = identity.split('::');
    console.log(`[parseBlockchainIdentity] Split result: ${parts.length} parts found`);
    parts.forEach((part, index) => {
      console.log(`[parseBlockchainIdentity]   Part ${index}: "${part}"`);
    });

    if (parts.length < 2) {
      console.warn(`[parseBlockchainIdentity] ✗ Invalid identity format (less than 2 parts): ${identity}`);
      return { mspId: '', userCN: '' };
    }

    let mspId = '';
    let x509Part = '';

    console.log(`[parseBlockchainIdentity] Determining identity format...`);
    console.log(`[parseBlockchainIdentity] Checking parts[0]="${parts[0]}" and parts[1]="${parts[1]}"`);

    // Check if the format includes MSP ID prefix
    if (parts[0] !== 'x509' && parts[1] === 'x509') {
      // Format 1: "MSP::x509::CN=user,OU=client::..."
      // Part 0: MSP ID (e.g., "Mem.org.comMSP")
      mspId = parts[0];
      // Part 2: X509 DN string (e.g., "CN=user1,OU=client")
      x509Part = parts[2];
      console.log(`[parseBlockchainIdentity] ✓ Format 1 detected (with MSP prefix)`);
      console.log(`[parseBlockchainIdentity]   MSP ID (parts[0]): "${mspId}"`);
      console.log(`[parseBlockchainIdentity]   X509 part (parts[2]): "${x509Part}"`);
    } else if (parts[0] === 'x509') {
      // Format 2: "x509::CN=user,OU=client::..." (actual NFT query format)
      // Part 0: "x509"
      // Part 1: X509 DN string (e.g., "CN=user3,OU=client")
      mspId = '';
      x509Part = parts[1];
      console.log(`[parseBlockchainIdentity] ✓ Format 2 detected (without MSP prefix - NFT query format)`);
      console.log(`[parseBlockchainIdentity]   MSP ID: (empty)`);
      console.log(`[parseBlockchainIdentity]   X509 part (parts[1]): "${x509Part}"`);
    } else {
      console.warn(`[parseBlockchainIdentity] ✗ Unrecognized identity format`);
      console.warn(`[parseBlockchainIdentity]   Expected: parts[0]='x509' OR (parts[0]!=x509 AND parts[1]='x509')`);
      console.warn(`[parseBlockchainIdentity]   Got: parts[0]='${parts[0]}', parts[1]='${parts[1]}'`);
      return { mspId: '', userCN: '' };
    }

    // Extract CN (Common Name) from the X509 DN
    // The CN we want is the first one (user CN), not the CA CN
    console.log(`[parseBlockchainIdentity] Extracting CN (Common Name) from X509 part...`);
    console.log(`[parseBlockchainIdentity] Using regex: /CN=([^,]+)/`);
    const cnMatch = x509Part.match(/CN=([^,]+)/);
    console.log(`[parseBlockchainIdentity] Regex match result:`, cnMatch);

    const userCN = cnMatch ? cnMatch[1] : '';

    if (userCN) {
      console.log(`[parseBlockchainIdentity] ✓ Successfully extracted User CN: "${userCN}"`);
    } else {
      console.warn(`[parseBlockchainIdentity] ✗ Failed to extract User CN from X509 part`);
    }

    console.log(`[parseBlockchainIdentity] ========== Parsing Complete ==========`);
    console.log(`[parseBlockchainIdentity] Final result:`);
    console.log(`[parseBlockchainIdentity]   MSP ID: "${mspId}"`);
    console.log(`[parseBlockchainIdentity]   User CN: "${userCN}"`);

    return { mspId, userCN };
  } catch (error) {
    console.error(`[parseBlockchainIdentity] ✗✗✗ Error parsing identity:`, error);
    console.error(`[parseBlockchainIdentity] Error details:`, {
      errorMessage: error.message,
      errorStack: error.stack
    });
    return { mspId: '', userCN: '' };
  }
}

/**
 * Find participant by FT (Fungible Token) balance
 * For FT tokens, we query the balance of each participant and find who has a non-zero balance
 *
 * @param participantBindings - Map of participant bindings
 * @param tokenName - The FT token name to query
 * @param ercChaincodeUrl - The ERC chaincode URL for querying
 * @returns The participant ID that has a non-zero balance, or null if not found
 */
async function findParticipantByFTBalance(
  participantBindings: Map<string, ParticipantBinding>,
  tokenName: string,
  ercChaincodeUrl: string | null
): Promise<string | null> {
  console.log(`[findParticipantByFTBalance] Querying balance for FT token "${tokenName}"`);
  console.log(`[findParticipantByFTBalance] ERC chaincode URL:`, ercChaincodeUrl);

  if (!ercChaincodeUrl) {
    console.warn(`[findParticipantByFTBalance] No ERC chaincode URL provided for token "${tokenName}"`);
    return null;
  }

  try {
    // Import fireflyAPI dynamically
    const { fireflyAPI } = await import('@/api/apiConfig.ts');

    // Extract base API URL from ercChaincodeUrl
    const urlMatch = ercChaincodeUrl.match(/^(https?:\/\/[^\/]+\/api\/v1\/namespaces\/[^\/]+\/apis)\/(.+)$/);
    if (!urlMatch) {
      console.error(`[findParticipantByFTBalance] Invalid ERC chaincode URL format: ${ercChaincodeUrl}`);
      return null;
    }

    const baseApisUrl = urlMatch[1];
    const registeredApiName = urlMatch[2];

    console.log(`[findParticipantByFTBalance] Base APIs URL: ${baseApisUrl}`);
    console.log(`[findParticipantByFTBalance] Registered API name: ${registeredApiName}`);

    // Iterate through all participant bindings with 'equal' validation type
    for (const [participantId, binding] of participantBindings.entries()) {
      if (binding.selectedValidationType === 'equal') {
        console.log(`[findParticipantByFTBalance] Checking participant: "${participantId}"`);

        // Extract user identity from binding
        // Try to get the x509 identity or username
        let userIdentity: string | null = null;

        // Method 1: Try x509 attribute
        if (binding.Attr && Array.isArray(binding.Attr)) {
          const x509Attr = binding.Attr.find(attr => attr.attr === 'x509');
          if (x509Attr && x509Attr.value) {
            try {
              const parts = x509Attr.value.split('@');
              const x509Value = parts[0];
              userIdentity = atob(x509Value); // Decode base64
              console.log(`[findParticipantByFTBalance] Extracted user identity from x509: "${userIdentity}"`);
            } catch (decodeError) {
              console.warn(`[findParticipantByFTBalance] Failed to decode x509:`, decodeError);
            }
          }
        }

        // Method 2: Use selectedUser as fallback
        if (!userIdentity && binding.selectedUser) {
          userIdentity = binding.selectedUser.split('@')[0]; // Extract username part
          console.log(`[findParticipantByFTBalance] Using selectedUser as identity: "${userIdentity}"`);
        }

        if (!userIdentity) {
          console.log(`[findParticipantByFTBalance] No identity found for participant "${participantId}", skipping`);
          continue;
        }

        // Query balance for this user
        // FT balance query: BalanceOf(account)
        const queryUrl = `${baseApisUrl}/${registeredApiName}/query/BalanceOf`;
        console.log(`[findParticipantByFTBalance] Querying balance: ${queryUrl}`);

        try {
          const response = await fireflyAPI.post(queryUrl, {
            input: {
              account: userIdentity
            }
          });

          console.log(`[findParticipantByFTBalance] Balance response for "${participantId}":`, response.data);

          // Extract balance from response
          let balance: number = 0;
          if (response.data?.output !== undefined) {
            balance = parseInt(response.data.output, 10) || 0;
          } else if (typeof response.data === 'number') {
            balance = response.data;
          } else if (typeof response.data === 'string') {
            balance = parseInt(response.data, 10) || 0;
          }

          console.log(`[findParticipantByFTBalance] Parsed balance for "${participantId}": ${balance}`);

          // If balance > 0, we found the owner
          if (balance > 0) {
            console.log(`[findParticipantByFTBalance] ✓✓✓ Found owner! Participant "${participantId}" has balance ${balance}`);
            return participantId;
          }
        } catch (queryError: any) {
          console.warn(`[findParticipantByFTBalance] Failed to query balance for participant "${participantId}":`, queryError.message);
          // Continue to next participant
        }
      }
    }

    console.warn(`[findParticipantByFTBalance] No participant found with non-zero balance for FT token "${tokenName}"`);
    return null;
  } catch (error) {
    console.error(`[findParticipantByFTBalance] Error querying FT balance:`, error);
    return null;
  }
}

/**
 * Find participant for distributive tokens
 * For distributive tokens, we need to query both the owner and users with usage rights
 *
 * @param participantBindings - Map of participant bindings
 * @param tokenId - The token ID to query
 * @param tokenInfo - Token information
 * @param ercChaincodeUrl - The ERC chaincode URL for querying
 * @returns The participant ID that owns the token, or null if not found
 */
async function findParticipantForDistributive(
  participantBindings: Map<string, ParticipantBinding>,
  tokenId: string,
  tokenInfo: { tokenType: string; assetType?: string; tokenName: string },
  ercChaincodeUrl: string | null
): Promise<string | null> {
  console.log(`[findParticipantForDistributive] Querying distributive token "${tokenId}"`);
  console.log(`[findParticipantForDistributive] Token info:`, tokenInfo);
  console.log(`[findParticipantForDistributive] ERC chaincode URL:`, ercChaincodeUrl);

  if (!ercChaincodeUrl) {
    console.warn(`[findParticipantForDistributive] No ERC chaincode URL provided for token "${tokenId}"`);
    return null;
  }

  try {
    // Import fireflyAPI dynamically
    const { fireflyAPI } = await import('@/api/apiConfig.ts');

    // Extract base API URL from ercChaincodeUrl
    const urlMatch = ercChaincodeUrl.match(/^(https?:\/\/[^\/]+\/api\/v1\/namespaces\/[^\/]+\/apis)\/(.+)$/);
    if (!urlMatch) {
      console.error(`[findParticipantForDistributive] Invalid ERC chaincode URL format: ${ercChaincodeUrl}`);
      return null;
    }

    const baseApisUrl = urlMatch[1];
    const registeredApiName = urlMatch[2];

    console.log(`[findParticipantForDistributive] Base APIs URL: ${baseApisUrl}`);
    console.log(`[findParticipantForDistributive] Registered API name: ${registeredApiName}`);

    // Step 1: Query OwnerOf to get the owner identity
    const queryUrl = `${baseApisUrl}/${registeredApiName}/query/OwnerOf`;
    console.log(`[findParticipantForDistributive] Querying OwnerOf: ${queryUrl}`);

    const response = await fireflyAPI.post(queryUrl, {
      input: {
        tokenId: tokenId
      }
    });

    console.log(`[findParticipantForDistributive] OwnerOf response:`, response.data);

    // Extract owner identity
    let ownerIdentity: string | null = null;
    if (response.data?.output) {
      ownerIdentity = response.data.output;
    } else if (typeof response.data === 'string' && response.data.includes('x509')) {
      ownerIdentity = response.data;
    } else if (response.data?.result) {
      ownerIdentity = response.data.result;
    } else if (response.data?.owner) {
      ownerIdentity = response.data.owner;
    }

    if (!ownerIdentity) {
      console.warn(`[findParticipantForDistributive] No owner identity found for token "${tokenId}"`);
      return null;
    }

    console.log(`[findParticipantForDistributive] Owner identity from blockchain: "${ownerIdentity}"`);

    // Step 2: Match the owner identity with participant bindings
    const { mspId, userCN } = parseBlockchainIdentity(ownerIdentity);
    console.log(`[findParticipantForDistributive] Parsed identity - MSP: ${mspId}, User CN: ${userCN}`);

    // Match with participant bindings (same logic as findParticipantByBlockchainIdentity)
    for (const [participantId, binding] of participantBindings.entries()) {
      if (binding.selectedValidationType === 'equal') {
        console.log(`[findParticipantForDistributive] Checking participant: "${participantId}"`);

        // Try to match by user CN
        if (binding.selectedUser === userCN) {
          console.log(`[findParticipantForDistributive] ✓✓✓ MATCHED! Participant "${participantId}" matched by user CN "${userCN}"`);
          return participantId;
        }

        // Try to match if selectedUser is in format "user@MSP"
        if (binding.selectedUser) {
          const selectedUserName = binding.selectedUser.split('@')[0];
          if (selectedUserName === userCN) {
            console.log(`[findParticipantForDistributive] ✓✓✓ MATCHED! Participant "${participantId}" matched by username "${userCN}"`);
            return participantId;
          }
        }

        // Try to match by x509 attribute
        if (binding.Attr && Array.isArray(binding.Attr)) {
          const x509Attr = binding.Attr.find(attr => attr.attr === 'x509');
          if (x509Attr && x509Attr.value) {
            try {
              const parts = x509Attr.value.split('@');
              const x509Value = parts[0];
              const decodedX509 = atob(x509Value);

              if (decodedX509 === ownerIdentity) {
                console.log(`[findParticipantForDistributive] ✓✓✓ MATCHED! Participant "${participantId}" matched by x509 identity`);
                return participantId;
              }
            } catch (decodeError) {
              console.warn(`[findParticipantForDistributive] Failed to decode x509:`, decodeError);
            }
          }
        }
      }
    }

    console.warn(`[findParticipantForDistributive] No matching participant found for distributive token "${tokenId}"`);
    return null;
  } catch (error: any) {
    console.error(`[findParticipantForDistributive] Error querying distributive token:`, error);
    console.error(`[findParticipantForDistributive] Error details:`, error.response?.data || error.message);
    return null;
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
