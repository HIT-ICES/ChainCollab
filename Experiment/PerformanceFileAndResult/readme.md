# Performance Experiment Manual

## 1. Deployment Environment

Deploy the environment and install the chaincode, register the Firefly interface, and obtain the chaincode namespace.

For example, BPMN2-9a0ded.

## 2. Modify the Experimental Code

Modify the chaincode's ContractName = "80-d37d45".
Obtain the container ID of the chaincode.

Run the experiment using the command:

``` python
python test.py test <batch> <chaincode container ID> <file to use: 2|10|20|...|200>
```

## 3. Run Experiments in Batch

Use the test.sh script and modify the sequence range.