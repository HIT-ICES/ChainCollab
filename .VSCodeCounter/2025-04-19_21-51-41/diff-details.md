# Diff Details

Date : 2025-04-19 21:51:41

Directory /home/logres/system/src/agent/cluster-manager

Total : 65 files,  -5632 codes, -942 comments, -274 blanks, all -6848 lines

[Summary](results.md) / [Details](details.md) / [Diff Summary](diff.md) / Diff Details

## Files
| filename | language | code | comment | blank | total |
| :--- | :--- | ---: | ---: | ---: | ---: |
| [IBC-AGENT/cluster-manager/build/docker-compose-template.yml](/IBC-AGENT/cluster-manager/build/docker-compose-template.yml) | YAML | 34 | 0 | 5 | 39 |
| [IBC-AGENT/cluster-manager/cmd/server/main.go](/IBC-AGENT/cluster-manager/cmd/server/main.go) | Go | 61 | 0 | 16 | 77 |
| [IBC-AGENT/cluster-manager/config.yml](/IBC-AGENT/cluster-manager/config.yml) | YAML | 22 | 0 | 1 | 23 |
| [IBC-AGENT/cluster-manager/go.mod](/IBC-AGENT/cluster-manager/go.mod) | Go Module File | 80 | 0 | 4 | 84 |
| [IBC-AGENT/cluster-manager/go.sum](/IBC-AGENT/cluster-manager/go.sum) | Go Checksum File | 255 | 0 | 1 | 256 |
| [IBC-AGENT/cluster-manager/internal/api/router.go](/IBC-AGENT/cluster-manager/internal/api/router.go) | Go | 153 | 0 | 35 | 188 |
| [IBC-AGENT/cluster-manager/internal/cluster/ipfscluster/ipfs-cluster.go](/IBC-AGENT/cluster-manager/internal/cluster/ipfscluster/ipfs-cluster.go) | Go | 110 | 0 | 23 | 133 |
| [IBC-AGENT/cluster-manager/internal/infra/db/mysql.go](/IBC-AGENT/cluster-manager/internal/infra/db/mysql.go) | Go | 17 | 0 | 5 | 22 |
| [IBC-AGENT/cluster-manager/internal/infra/db/types.go](/IBC-AGENT/cluster-manager/internal/infra/db/types.go) | Go | 6 | 0 | 3 | 9 |
| [IBC-AGENT/cluster-manager/internal/infra/logger/logger.go](/IBC-AGENT/cluster-manager/internal/infra/logger/logger.go) | Go | 14 | 0 | 4 | 18 |
| [IBC-AGENT/cluster-manager/internal/infra/logger/types.go](/IBC-AGENT/cluster-manager/internal/infra/logger/types.go) | Go | 4 | 0 | 2 | 6 |
| [IBC-AGENT/cluster-manager/internal/infra/mq/redis.go](/IBC-AGENT/cluster-manager/internal/infra/mq/redis.go) | Go | 77 | 0 | 16 | 93 |
| [IBC-AGENT/cluster-manager/internal/infra/mq/types.go](/IBC-AGENT/cluster-manager/internal/infra/mq/types.go) | Go | 57 | 0 | 11 | 68 |
| [IBC-AGENT/cluster-manager/internal/infra/registry.go](/IBC-AGENT/cluster-manager/internal/infra/registry.go) | Go | 83 | 0 | 18 | 101 |
| [IBC-AGENT/cluster-manager/internal/models/cluster.go](/IBC-AGENT/cluster-manager/internal/models/cluster.go) | Go | 21 | 0 | 6 | 27 |
| [IBC-AGENT/cluster-manager/internal/models/init.go](/IBC-AGENT/cluster-manager/internal/models/init.go) | Go | 20 | 0 | 5 | 25 |
| [IBC-AGENT/cluster-manager/internal/models/provider.go](/IBC-AGENT/cluster-manager/internal/models/provider.go) | Go | 21 | 0 | 5 | 26 |
| [IBC-AGENT/cluster-manager/internal/models/task.go](/IBC-AGENT/cluster-manager/internal/models/task.go) | Go | 28 | 0 | 5 | 33 |
| [IBC-AGENT/cluster-manager/internal/provider/docker\_provider.go](/IBC-AGENT/cluster-manager/internal/provider/docker_provider.go) | Go | 236 | 0 | 41 | 277 |
| [IBC-AGENT/cluster-manager/internal/provider/interface.go](/IBC-AGENT/cluster-manager/internal/provider/interface.go) | Go | 51 | 0 | 8 | 59 |
| [IBC-AGENT/cluster-manager/internal/repository/cluster\_manager.go](/IBC-AGENT/cluster-manager/internal/repository/cluster_manager.go) | Go | 32 | 0 | 8 | 40 |
| [IBC-AGENT/cluster-manager/internal/repository/provider\_manager.go](/IBC-AGENT/cluster-manager/internal/repository/provider_manager.go) | Go | 35 | 0 | 7 | 42 |
| [IBC-AGENT/cluster-manager/internal/repository/task\_manager.go](/IBC-AGENT/cluster-manager/internal/repository/task_manager.go) | Go | 75 | 0 | 12 | 87 |
| [IBC-AGENT/cluster-manager/internal/task/handler.go](/IBC-AGENT/cluster-manager/internal/task/handler.go) | Go | 90 | 0 | 21 | 111 |
| [IBC-AGENT/cluster-manager/internal/task/ipfs\_handler.go](/IBC-AGENT/cluster-manager/internal/task/ipfs_handler.go) | Go | 90 | 0 | 17 | 107 |
| [IBC-AGENT/cluster-manager/internal/task/types.go](/IBC-AGENT/cluster-manager/internal/task/types.go) | Go | 8 | 0 | 3 | 11 |
| [IBC-AGENT/cluster-manager/internal/task/worker.go](/IBC-AGENT/cluster-manager/internal/task/worker.go) | Go | 50 | 0 | 10 | 60 |
| [IBC-AGENT/cluster-manager/internal/utils/random.go](/IBC-AGENT/cluster-manager/internal/utils/random.go) | Go | 14 | 0 | 5 | 19 |
| [IBC-AGENT/cluster-manager/scripts/config.yaml](/IBC-AGENT/cluster-manager/scripts/config.yaml) | YAML | 40 | 0 | 5 | 45 |
| [IBC-AGENT/cluster-manager/temp/docker-compose.yml](/IBC-AGENT/cluster-manager/temp/docker-compose.yml) | YAML | 20 | 0 | 5 | 25 |
| [IBC-AGENT/cluster-manager/test/docker.go](/IBC-AGENT/cluster-manager/test/docker.go) | Go | 25 | 0 | 5 | 30 |
| [IBC-BACKEND/docker-compose.yml](/IBC-BACKEND/docker-compose.yml) | YAML | -19 | 0 | -2 | -21 |
| [IBC-BACKEND/instance\_create\_response.json](/IBC-BACKEND/instance_create_response.json) | JSONC | -1 | 0 | 0 | -1 |
| [IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/bpmnChoreography.go](/IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/bpmnChoreography.go) | Go | -15 | 0 | -6 | -21 |
| [IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/go.mod](/IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/go.mod) | Go Module File | -13 | 0 | -5 | -18 |
| [IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/go.sum](/IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/go.sum) | Go Checksum File | -156 | 0 | -1 | -157 |
| [IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/test.fabric](/IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/test.fabric) | JSONC | -19 | 0 | -1 | -20 |
| [IBC-BACKEND/opt/config/ccp\_template.yaml](/IBC-BACKEND/opt/config/ccp_template.yaml) | YAML | -63 | 0 | 0 | -63 |
| [IBC-BACKEND/opt/config/configtx.yaml](/IBC-BACKEND/opt/config/configtx.yaml) | YAML | -269 | -267 | -73 | -609 |
| [IBC-BACKEND/opt/config/core.yaml](/IBC-BACKEND/opt/config/core.yaml) | YAML | -237 | -455 | -73 | -765 |
| [IBC-BACKEND/opt/config/manifest.json](/IBC-BACKEND/opt/config/manifest.json) | JSONC | -64 | 0 | 0 | -64 |
| [IBC-BACKEND/opt/config/msp\_config\_template.yaml](/IBC-BACKEND/opt/config/msp_config_template.yaml) | YAML | -14 | 0 | -1 | -15 |
| [IBC-BACKEND/opt/config/orderer.yaml](/IBC-BACKEND/opt/config/orderer.yaml) | YAML | -105 | -219 | -47 | -371 |
| [IBC-BACKEND/opt/firefly-go/chaincode/contract.go](/IBC-BACKEND/opt/firefly-go/chaincode/contract.go) | Go | -92 | 0 | -8 | -100 |
| [IBC-BACKEND/opt/firefly-go/chaincode/contract\_test.go](/IBC-BACKEND/opt/firefly-go/chaincode/contract_test.go) | Go | -36 | 0 | -9 | -45 |
| [IBC-BACKEND/opt/firefly-go/chaincode/mocks/chaincodestub.go](/IBC-BACKEND/opt/firefly-go/chaincode/mocks/chaincodestub.go) | Go | -2,700 | 0 | -216 | -2,916 |
| [IBC-BACKEND/opt/firefly-go/chaincode/mocks/clientidentity.go](/IBC-BACKEND/opt/firefly-go/chaincode/mocks/clientidentity.go) | Go | -373 | 0 | -32 | -405 |
| [IBC-BACKEND/opt/firefly-go/chaincode/mocks/statequeryiterator.go](/IBC-BACKEND/opt/firefly-go/chaincode/mocks/statequeryiterator.go) | Go | -215 | 0 | -21 | -236 |
| [IBC-BACKEND/opt/firefly-go/chaincode/mocks/transaction.go](/IBC-BACKEND/opt/firefly-go/chaincode/mocks/transaction.go) | Go | -151 | 0 | -16 | -167 |
| [IBC-BACKEND/opt/firefly-go/firefly.go](/IBC-BACKEND/opt/firefly-go/firefly.go) | Go | -18 | 0 | -6 | -24 |
| [IBC-BACKEND/opt/firefly-go/go.mod](/IBC-BACKEND/opt/firefly-go/go.mod) | Go Module File | -35 | 0 | -4 | -39 |
| [IBC-BACKEND/opt/firefly-go/go.sum](/IBC-BACKEND/opt/firefly-go/go.sum) | Go Checksum File | -167 | 0 | -1 | -168 |
| [IBC-BACKEND/opt/oracle-go/go.mod](/IBC-BACKEND/opt/oracle-go/go.mod) | Go Module File | -6 | -1 | -3 | -10 |
| [IBC-BACKEND/opt/oracle-go/go.sum](/IBC-BACKEND/opt/oracle-go/go.sum) | Go Checksum File | -154 | 0 | -1 | -155 |
| [IBC-BACKEND/opt/oracle-go/oracle/oracle.go](/IBC-BACKEND/opt/oracle-go/oracle/oracle.go) | Go | -104 | 0 | -29 | -133 |
| [IBC-BACKEND/opt/oracle-go/oracle/oracle\_client.go](/IBC-BACKEND/opt/oracle-go/oracle/oracle_client.go) | Go | -26 | 0 | -5 | -31 |
| [IBC-BACKEND/opt/oracle-go/oracle\_stub.go](/IBC-BACKEND/opt/oracle-go/oracle_stub.go) | Go | -17 | 0 | -5 | -22 |
| [IBC-BACKEND/opt/oracleFFI.json](/IBC-BACKEND/opt/oracleFFI.json) | JSONC | -40 | 0 | 0 | -40 |
| [IBC-BACKEND/opt/stateCharts-go/go.mod](/IBC-BACKEND/opt/stateCharts-go/go.mod) | Go Module File | -3 | 0 | -3 | -6 |
| [IBC-BACKEND/opt/stateCharts-go/go.sum](/IBC-BACKEND/opt/stateCharts-go/go.sum) | Go Checksum File | -2,110 | 0 | -1 | -2,111 |
| [IBC-BACKEND/opt/stateCharts-go/stateCharts/stateCharts\_client.go](/IBC-BACKEND/opt/stateCharts-go/stateCharts/stateCharts_client.go) | Go | -37 | 0 | -11 | -48 |
| [IBC-BACKEND/opt/stateCharts-go/stateCharts\_stub.go](/IBC-BACKEND/opt/stateCharts-go/stateCharts_stub.go) | Go | -17 | 0 | -5 | -22 |
| [IBC-BACKEND/opt/statechartFFI.json](/IBC-BACKEND/opt/statechartFFI.json) | JSONC | -60 | 0 | 0 | -60 |
| [IBC-BACKEND/opt/statecharts-javascript-2.2/package.json](/IBC-BACKEND/opt/statecharts-javascript-2.2/package.json) | JSONC | -50 | 0 | -1 | -51 |
| [IBC-BACKEND/requirements.txt](/IBC-BACKEND/requirements.txt) | pip requirements | -75 | 0 | 0 | -75 |

[Summary](results.md) / [Details](details.md) / [Diff Summary](diff.md) / Diff Details