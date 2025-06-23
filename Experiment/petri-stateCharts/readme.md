# Test-network启动命令

 ./network.sh up
 ./network.sh createChannel
 ./network.sh deployCC -ccn basic -ccp /home/shenxz-lab/code/ChainCollab/Experiment/petri-stateCharts/petriNet/chaincode-go -ccl go
 bash test.sh | tee result.txt

 # Test-network配置修改
     # Batch Size: Controls the number of messages batched into a block
    BatchSize:

        # Max Message Count: The maximum number of messages to permit in a batch
        MaxMessageCount: 10000

        # Absolute Max Bytes: The absolute maximum number of bytes allowed for
        # the serialized messages in a batch.
        AbsoluteMaxBytes: 99 MB

        # Preferred Max Bytes: The preferred maximum number of bytes allowed for
        # the serialized messages in a batch. A message larger than the preferred
        # max bytes will result in a batch larger than preferred max bytes.
        PreferredMaxBytes: 90 MB
