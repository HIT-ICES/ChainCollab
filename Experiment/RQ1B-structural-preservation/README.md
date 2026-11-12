# RQ1B: Structural preservation

The checker extracts typed attributed graphs from BPMN and B2CDSL and compares them against the [mapping contract](contracts/default_mapping_contract.json). Start with the [eleven-case batch report](cases/batch_summary.md). Individual reports, generated DSL, and source-to-DSL trace links are under [cases](cases/).

Run the [structural batch command](../README.md#rq1rq3-verification) with the [archived BPMN fixtures](../fixtures/). The [path traceability extension](rq3-path-traceability/README.md) follows RQ3 path operations back through the structural trace links.
