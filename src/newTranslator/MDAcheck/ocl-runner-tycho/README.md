# Eclipse OCL runner

The Maven Tycho project runs Complete OCL validation over XMI instances using an Ecore metamodel. It obtains Eclipse OCL and EMF bundles from the Eclipse p2 repository declared in [pom.xml](pom.xml). Use Java 17 and Maven with access to that repository.

To validate the paper's 450-model dataset, use the [RQ1A command in the experiment index](../../../../Experiment/README.md). For an individual model, run from this directory:

```bash
mvn -f pom.xml -Dtycho.disableP2Mirrors=true \
  -Decore=/absolute/path/to/b2c.ecore -Docl=/absolute/path/to/check.ocl \
  -Dxmi=/absolute/path/to/model.xmi integration-test
```

For a batch, [run_ocl_validate_batch.sh](../run_ocl_validate_batch.sh) accepts the XMI directory, Ecore file, OCL file, and output directory. It walks the input directory recursively and writes aggregate and per-model JSON reports. The test harness collects violations across the corpus so expected negative examples are represented in the report.
