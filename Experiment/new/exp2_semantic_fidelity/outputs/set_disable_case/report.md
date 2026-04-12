# Semantic Fidelity Report: set_disable_case

- DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/set_disable_case/set_disable_case.b2c`
- Go: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/set_disable_case/set_disable_case.go`
- Solidity: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/set_disable_case/set_disable_case.sol`

## DSL Statistics

- participants: 2
- globals: 2
- messages: 3
- events: 2
- gateways: 1
- businessrules: 0
- flows: 5

## Go

- verdict: PARTIAL
- flow matched: 4 / 5
- flow coverage: 0.8
- unsupported: none

### Missing Structure

- globals: missing=[] extra=[]
- messages: missing=[] extra=[]
- events: missing=[] extra=[]
- gateways: missing=[] extra=[]
- businessrules: missing=[] extra=[]

### Unmatched Rules

- flow_002: trigger_match=True ratio=0.5 missing=[{'op': 'set', 'var': 'Counter', 'value': "''"}] notes=[]

## Solidity

- verdict: PASS
- flow matched: 5 / 5
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
