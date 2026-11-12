# RQ1A: Target-model legality

This experiment validates generated B2CDSL models against the Ecore metamodel and 43 Complete OCL constraints. The [XMI dataset](dataset/) contains 11 valid models, 299 random mutations, and 140 targeted mutations. See the [dataset manifest](dataset/dataset_manifest.json) and [rule coverage report](dataset/coverage_completion_report.md).

Run the [RQ1A validation command](../README.md#rq1rq3-verification) with Java 17 and Maven. The [checker](../../src/newTranslator/MDAcheck/) writes the reports to the output directory supplied on the command line.
