# newTranslator-fork

This fork adds **BPMN split generation** on top of the base `newTranslator`.

## Capability

Input:
- one BPMN file
- optional split marker(s), or marker auto-detection from BPMN `documentation`

Output:
- full artifacts from base translator (`.b2c` + full Solidity contract)
- split artifacts:
  - `split.dsl`
  - two split contracts (`SubmodelA.sol`, `SubmodelB.sol`)
  - `split-plan.json`

## Marker convention

You can mark split points in BPMN `documentation` JSON:

```json
{"splitPoint": true}
```

Or pass manual marker ids:

```bash
python3 split_translator.py path/to/model.bpmn --split-point-id Activity_123
```

## Quick start

```bash
cd /home/logres/system/src/newTranslator-fork
python3 split_translator.py /home/logres/system/Experiment/CaseTest/SupplyChain.bpmn
```

Output default root:

`/home/logres/system/src/newTranslator-fork/build_split/<case>/`
