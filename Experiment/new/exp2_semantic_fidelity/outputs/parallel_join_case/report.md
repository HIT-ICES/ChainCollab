# Semantic Fidelity Report: parallel_join_case

- DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/parallel_join_case/parallel_join_case.b2c`
- Go: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/parallel_join_case/parallel_join_case.go`
- Solidity: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/parallel_join_case/parallel_join_case.sol`

## DSL Statistics

- participants: 3
- globals: 1
- messages: 3
- events: 2
- gateways: 2
- businessrules: 0
- flows: 6

## Go

- verdict: PARTIAL
- flow matched: 5 / 6
- flow coverage: 0.8333
- unsupported: none

### Missing Structure

- globals: missing=[] extra=[]
- messages: missing=[] extra=[]
- events: missing=[] extra=[]
- gateways: missing=[] extra=[]
- businessrules: missing=[] extra=[]

### Unmatched Rules

- flow_005: trigger_match=False ratio=0.0 missing=[{'op': 'enable', 'target': 'MsgC'}] notes=['no matching handler']

## Solidity

- verdict: PASS
- flow matched: 6 / 6
- flow coverage: 1.0
- unsupported: none

### Missing Structure

- globals: missing=[] extra=[]
- messages: missing=[] extra=[]
- events: missing=[] extra=[]
- gateways: missing=[] extra=[]
- businessrules: missing=[] extra=['PlaceholderBusinessRule']

### Unmatched Rules

- none

## Conclusion

- final verdict: PARTIAL
