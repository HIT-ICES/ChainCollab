# RQ1C: Bounded behavioral preservation

This experiment constructs behavioral transition systems for BPMN and B2CDSL and compares path sets, step transitions, and final states under the bound `K = (30, 2, 200)`. The [case archives](cases/) include the model inputs, comparison reports, and the 75 logical paths used in [RQ3](../RQ3-runtime-trace-consistency/README.md).

Run the [UBTS command](../README.md#rq1rq3-verification) with `EXP1C_OUTPUT_ROOT` set to a new output directory. The default case is SupplyChainPaper. Set `EXP1C_CASE_NAME` to select another archived case.
