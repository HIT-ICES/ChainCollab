# Semantic Fidelity Report: event_flow_case

- DSL: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/event_flow_case/event_flow_case.b2c`
- Go: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/event_flow_case/event_flow_case.go`
- Solidity: `/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/event_flow_case/event_flow_case.sol`

## DSL Statistics

- participants: 2
- globals: 1
- messages: 1
- events: 3
- gateways: 0
- businessrules: 0
- flows: 3

## Go

- verdict: PARTIAL
- flow matched: 2 / 3
- flow coverage: 0.6667
- unsupported: none

### Missing Structure

- globals: missing=[] extra=[]
- messages: missing=[] extra=[]
- events: missing=['MidEvent_1'] extra=[]
- gateways: missing=[] extra=[]
- businessrules: missing=[] extra=[]

### Unmatched Rules

- flow_003: trigger_match=False ratio=0.0 missing=[{'op': 'enable', 'target': 'EndEvent_1'}] notes=['no matching handler']

## Solidity

- verdict: PARTIAL
- flow matched: 2 / 3
- flow coverage: 0.6667
- unsupported: none

### Missing Structure

- globals: missing=[] extra=[]
- messages: missing=[] extra=[]
- events: missing=[] extra=[]
- gateways: missing=[] extra=['PlaceholderGateway']
- businessrules: missing=[] extra=['PlaceholderBusinessRule']

### Unmatched Rules

- flow_003: trigger_match=False ratio=0.0 missing=[{'op': 'enable', 'target': 'EndEvent_1'}] notes=['no matching handler']

## Conclusion

- final verdict: PARTIAL
