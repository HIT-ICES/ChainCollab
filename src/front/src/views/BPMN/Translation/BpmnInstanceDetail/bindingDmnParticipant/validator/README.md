# Instance Validation

This module provides validation for BPMN instance creation, specifically checking token ownership and participant permissions for blockchain operations.

## Features

The validator checks the following aspects:

### 1. Token Ownership Tracking
- Tracks token ownership through the process flow
- Validates that operations are performed by authorized participants
- Ensures tokens are owned before burn/transfer operations

### 2. Operation-Specific Validation

#### Mint Operation
- Creates new tokens and assigns ownership to the minter
- Requires specific user binding for the minting participant
- Validates that the minter has proper authorization

#### Burn Operation
- Requires the caller to own the token being burned
- Removes token from ownership tracking after burn
- Reports error if caller doesn't own the token

#### Transfer Operation
- Requires the caller to own the token being transferred
- Validates that recipient (callee) is properly bound
- Updates token ownership to the recipient after transfer
- Ensures recipient participants are bound to valid identities

#### Grant/Revoke Usage Rights
- Requires the caller to own the token
- Validates that grantee/revokee is specified
- Checks proper participant bindings

#### Branch/Merge (Value-Added Tokens)
- Validates ownership of source tokens
- Updates ownership to the branching/merging participant
- Specific to value-added asset types

#### Query Operation
- No ownership changes
- **No ownership requirements** - any participant can query
- Open to all participants regardless of token ownership
- Only validates proper participant binding for the caller

### 3. Token Type Validation
- **FT (Fungible Tokens)**: Validates that `tokenNumber` is specified for non-query operations
- **NFT (Non-Fungible Tokens)**:
  - Validates `tokenId` ownership and transfers
  - **Critical**: Once an NFT is burned, no further operations (except query) can be performed on it
  - NFT tokens are unique and cannot be re-minted after being destroyed
- **Distributive Tokens**: Validates usage rights operations
- **Value-Added Tokens**: Validates branch/merge operations and reference token IDs

### 4. NFT Burn Lifecycle Validation
- **Critical Rule**: NFT tokens cannot be used after being burned
- Once a burn operation is performed on an NFT:
  - Transfer operations are blocked
  - Burn operations are blocked (cannot burn twice)
  - Grant/revoke usage rights are blocked
  - Branch/merge operations are blocked
  - Only query operations remain allowed (to check historical data)
- **FT Exception**: FT tokens CAN be re-minted after burn, as they are fungible
- Example error: "Cannot perform 'transfer' on token 'TokenA (ID: 123)' because it was already burned in task 'Burn TokenA'. NFT tokens cannot be used after being destroyed."

### 5. Participant Binding Validation
- Ensures all callers are bound to participants
- Validates callees (recipients) are properly bound
- Checks binding types (equal vs. group)
- Verifies specific user bindings for sensitive operations (e.g., minting)

### 6. ERC Contract Binding Consistency
- **Critical**: Validates that the same token uses the same ERC contract across all operations
- Prevents data inconsistency by ensuring mint, transfer, burn, etc. all use the same contract
- Reports errors when different tasks operating on the same token are bound to different contracts
- Example error: "Token 'rawMaterial' must use the same ERC contract across all operations. Task 'mint rawMaterial' uses 'ERC721Contract_A', but task 'burn rawMaterial' uses 'ERC721Contract_B'"

## Usage

### In the Modal Component

The validation is integrated into the `ParticipantDmnBindingModal` component:

```tsx
import { validateInstance, formatValidationErrors } from "./validator/InstanceValidator";

// In component:
const handleValidation = async () => {
  const bpmn = await retrieveBPMN(bpmnId);
  const result = await validateInstance(
    bpmn.content,
    showBindingParticipantValueMap,
    showTaskERCMap
  );

  if (result.isValid) {
    message.success('Validation passed!');
  } else {
    // Display errors
    setValidationErrors(result.errors);
  }
};
```

### Validation Button

Click the "Validate Instance" button in the modal to:
1. Check all token operations against participant bindings
2. Verify token ownership chains through the process
3. Display detailed error and warning messages

## Validation Result Structure

```typescript
interface ValidationResult {
  isValid: boolean;      // true if no errors (warnings are ok)
  errors: ValidationError[];
}

interface ValidationError {
  taskId: string;        // ID of the task with the error
  taskName: string;      // Name of the task for display
  message: string;       // Detailed error message
  severity: 'error' | 'warning';
}
```

### Error Severity Levels

- **Error**: Critical issues that will likely cause the instance to fail. Must be fixed before deployment.
  - Missing caller binding
  - Token ownership violations
  - Missing required fields (e.g., callee for transfer)
  - Unknown operation types

- **Warning**: Potential issues that may not prevent execution but should be reviewed.
  - Usage rights operations without ownership
  - Missing token numbers for FT operations
  - Unspecified optional fields

## Validation Rules

### Ownership Rules
1. Tokens must be minted before they can be used
2. Only token owners can burn or transfer tokens
3. Ownership transfers to the recipient after a transfer operation
4. Multiple participants can own the same token (for group scenarios)

### Participant Binding Rules
1. All callers must be bound to a participant
2. All callees (recipients) must be bound to a participant
3. Mint operations should have specific user bindings (equal type)
4. Group bindings are allowed for most operations

### Token Flow Rules
1. Token lifecycle follows the sequence: mint → operations → burn
2. Tokens cannot be used before being minted
3. Tokens cannot be used after being burned
4. Value-added tokens can reference other tokens via `refTokenIds`

## Example Scenarios

### Valid Flow
```
1. Mint (Manufacturer) → Token1 owned by Manufacturer
2. Transfer (Manufacturer → Bulk buyer) → Token1 owned by Bulk buyer
3. Burn (Bulk buyer) → Token1 removed
✅ All validations pass
```

### Invalid Flow
```
1. Mint (Manufacturer) → Token1 owned by Manufacturer
2. Burn (Supplier) → Token1
❌ Error: Supplier doesn't own Token1
```

### Missing Binding
```
1. Mint (Manufacturer) → Token1
2. Transfer (Manufacturer → ???) → No callee specified
❌ Error: Transfer requires a recipient
```

### Query Operations (No Ownership Required)
```
1. Mint (Manufacturer) → Token1 owned by Manufacturer
2. Query (Supplier) → Query Token1
✅ Valid: Supplier can query even without owning Token1
3. Query (Bulk buyer) → Query Token1
✅ Valid: Any participant can query token information
4. Transfer (Manufacturer → Bulk buyer) → Token1 owned by Bulk buyer
5. Query (Supplier) → Query Token1
✅ Valid: Supplier can still query after ownership change
```

### NFT Burn Lifecycle (Cannot Use After Burn)
```
1. Mint (Manufacturer) → NFT Token1 (ID: 123) owned by Manufacturer
2. Transfer (Manufacturer → Supplier) → NFT Token1 owned by Supplier
3. Burn (Supplier) → NFT Token1 destroyed
4. Transfer (Supplier → Bulk buyer) → NFT Token1
❌ Error: Cannot perform "transfer" on token "Token1 (ID: 123)" because it was already burned in task "Burn Token1"
```

### FT Can Be Re-minted (Unlike NFT)
```
1. Mint (Manufacturer) → FT Token_A (100 units) owned by Manufacturer
2. Transfer (Manufacturer → Supplier) → FT Token_A owned by Supplier
3. Burn (Supplier) → FT Token_A destroyed
4. Mint (Manufacturer) → FT Token_A (50 units) owned by Manufacturer
✅ Valid: FT tokens can be re-minted after burn because they are fungible
```

### NFT Cannot Be Re-minted (After Burn)
```
1. Mint (Manufacturer) → NFT Token1 (ID: 123) owned by Manufacturer
2. Burn (Manufacturer) → NFT Token1 destroyed
3. Mint (Manufacturer) → NFT Token1 (ID: 123)
❌ Error: Cannot perform "mint" on token "Token1 (ID: 123)" - wait, actually mint is allowed to create new tokens
   Note: If using same ID after burn, this creates a NEW token with same ID
```

### Query After Burn (Always Allowed)
```
1. Mint (Manufacturer) → NFT Token1 (ID: 123) owned by Manufacturer
2. Burn (Manufacturer) → NFT Token1 destroyed
3. Query (Supplier) → Query NFT Token1
✅ Valid: Query operations are always allowed, even for burned tokens (to check history)
```


## Extending the Validator

To add custom validation rules:

1. Open `InstanceValidator.ts`
2. Add a new case in the operation switch statement:
```typescript
case 'your_operation':
  // Your validation logic
  if (invalidCondition) {
    errors.push({
      taskId,
      taskName,
      message: 'Your error message',
      severity: 'error'
    });
  }
  break;
```

3. Update token ownership if needed:
```typescript
tokenOwnership.set(effectiveTokenId, [newOwner]);
```

## Troubleshooting

### "Caller is not bound to any participant"
- Ensure the participant is selected in the "Binding Participants" section
- Check that the participant name matches the one used in the BPMN diagram

### "Operation requires caller to own token"
- Verify the token flow: check if a mint operation precedes this operation
- Ensure token IDs are consistent across operations
- Check if a previous transfer changed ownership

### "Transfer recipient is not bound"
- Select a recipient in the task configuration
- Ensure the recipient participant is bound in the "Binding Participants" section

### "Token must use the same ERC contract across all operations"
- Check all tasks operating on the same token
- Ensure they are all bound to the same ERC contract in "Binding Tasks to ERC"
- If you see this error, unbind and rebind tasks to use a consistent contract

## Technical Details

- The validator parses BPMN XML using DOMParser
- It iterates through all tasks and tracks state (token ownership) through the flow
- Documentation fields in BPMN elements contain operation metadata (JSON format)
- The validator is stateless and can be run multiple times without side effects
