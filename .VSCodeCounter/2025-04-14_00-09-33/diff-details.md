# Diff Details

Date : 2025-04-14 00:09:33

Directory /home/logres/system/src/backend

Total : 68 files,  6211 codes, 941 comments, 390 blanks, all 7542 lines

[Summary](results.md) / [Details](details.md) / [Diff Summary](diff.md) / Diff Details

## Files
| filename | language | code | comment | blank | total |
| :--- | :--- | ---: | ---: | ---: | ---: |
| [IBC-AGENT/cluster-manager/build/docker-compose-template.yml](/IBC-AGENT/cluster-manager/build/docker-compose-template.yml) | YAML | -33 | 0 | -5 | -38 |
| [IBC-AGENT/cluster-manager/cmd/server/main.go](/IBC-AGENT/cluster-manager/cmd/server/main.go) | Go | -47 | 0 | -12 | -59 |
| [IBC-AGENT/cluster-manager/config.yml](/IBC-AGENT/cluster-manager/config.yml) | YAML | -18 | 0 | -1 | -19 |
| [IBC-AGENT/cluster-manager/go.mod](/IBC-AGENT/cluster-manager/go.mod) | Go Module File | -79 | 0 | -4 | -83 |
| [IBC-AGENT/cluster-manager/go.sum](/IBC-AGENT/cluster-manager/go.sum) | Go Checksum File | -277 | 0 | -1 | -278 |
| [IBC-AGENT/cluster-manager/internal/api/router.go](/IBC-AGENT/cluster-manager/internal/api/router.go) | Go | -86 | 0 | -17 | -103 |
| [IBC-AGENT/cluster-manager/internal/cluster/interface.go](/IBC-AGENT/cluster-manager/internal/cluster/interface.go) | Go | -5 | 0 | -3 | -8 |
| [IBC-AGENT/cluster-manager/internal/cluster/ipfscluster/ipfs-cluster.go](/IBC-AGENT/cluster-manager/internal/cluster/ipfscluster/ipfs-cluster.go) | Go | -67 | 0 | -12 | -79 |
| [IBC-AGENT/cluster-manager/internal/cluster/ipfscluster/types.go](/IBC-AGENT/cluster-manager/internal/cluster/ipfscluster/types.go) | Go | 0 | 0 | -1 | -1 |
| [IBC-AGENT/cluster-manager/internal/infra/config.go](/IBC-AGENT/cluster-manager/internal/infra/config.go) | Go | -14 | 0 | -4 | -18 |
| [IBC-AGENT/cluster-manager/internal/infra/logger.go](/IBC-AGENT/cluster-manager/internal/infra/logger.go) | Go | -14 | 0 | -4 | -18 |
| [IBC-AGENT/cluster-manager/internal/infra/mysql.go](/IBC-AGENT/cluster-manager/internal/infra/mysql.go) | Go | -16 | 0 | -5 | -21 |
| [IBC-AGENT/cluster-manager/internal/infra/redis.go](/IBC-AGENT/cluster-manager/internal/infra/redis.go) | Go | -20 | 0 | -6 | -26 |
| [IBC-AGENT/cluster-manager/internal/infra/registry.go](/IBC-AGENT/cluster-manager/internal/infra/registry.go) | Go | -24 | 0 | -8 | -32 |
| [IBC-AGENT/cluster-manager/internal/models/cluster.go](/IBC-AGENT/cluster-manager/internal/models/cluster.go) | Go | -38 | 0 | -7 | -45 |
| [IBC-AGENT/cluster-manager/internal/models/cluster\_node.go](/IBC-AGENT/cluster-manager/internal/models/cluster_node.go) | Go | -16 | 0 | -3 | -19 |
| [IBC-AGENT/cluster-manager/internal/models/init.go](/IBC-AGENT/cluster-manager/internal/models/init.go) | Go | -13 | 0 | -4 | -17 |
| [IBC-AGENT/cluster-manager/internal/models/provider.go](/IBC-AGENT/cluster-manager/internal/models/provider.go) | Go | -11 | 0 | -3 | -14 |
| [IBC-AGENT/cluster-manager/internal/models/task.go](/IBC-AGENT/cluster-manager/internal/models/task.go) | Go | -20 | 0 | -3 | -23 |
| [IBC-AGENT/cluster-manager/internal/provider/docker/client.go](/IBC-AGENT/cluster-manager/internal/provider/docker/client.go) | Go | -16 | 0 | -4 | -20 |
| [IBC-AGENT/cluster-manager/internal/provider/docker/container.go](/IBC-AGENT/cluster-manager/internal/provider/docker/container.go) | Go | -37 | 0 | -7 | -44 |
| [IBC-AGENT/cluster-manager/internal/provider/docker/network.go](/IBC-AGENT/cluster-manager/internal/provider/docker/network.go) | Go | -35 | 0 | -7 | -42 |
| [IBC-AGENT/cluster-manager/internal/provider/docker/types.go](/IBC-AGENT/cluster-manager/internal/provider/docker/types.go) | Go | -8 | 0 | -2 | -10 |
| [IBC-AGENT/cluster-manager/internal/provider/interface.go](/IBC-AGENT/cluster-manager/internal/provider/interface.go) | Go | -6 | 0 | -3 | -9 |
| [IBC-AGENT/cluster-manager/internal/repository/cluster\_manager.go](/IBC-AGENT/cluster-manager/internal/repository/cluster_manager.go) | Go | -41 | 0 | -8 | -49 |
| [IBC-AGENT/cluster-manager/internal/repository/cluster\_node\_manager.go](/IBC-AGENT/cluster-manager/internal/repository/cluster_node_manager.go) | Go | -41 | 0 | -8 | -49 |
| [IBC-AGENT/cluster-manager/internal/repository/provider\_manager.go](/IBC-AGENT/cluster-manager/internal/repository/provider_manager.go) | Go | -34 | 0 | -7 | -41 |
| [IBC-AGENT/cluster-manager/internal/repository/task\_manager.go](/IBC-AGENT/cluster-manager/internal/repository/task_manager.go) | Go | -41 | 0 | -7 | -48 |
| [IBC-AGENT/cluster-manager/internal/task/handler.go](/IBC-AGENT/cluster-manager/internal/task/handler.go) | Go | -43 | 0 | -6 | -49 |
| [IBC-AGENT/cluster-manager/internal/task/types.go](/IBC-AGENT/cluster-manager/internal/task/types.go) | Go | -25 | 0 | -5 | -30 |
| [IBC-AGENT/cluster-manager/internal/task/worker.go](/IBC-AGENT/cluster-manager/internal/task/worker.go) | Go | -42 | 0 | -10 | -52 |
| [IBC-AGENT/cluster-manager/pkg/config/config.go](/IBC-AGENT/cluster-manager/pkg/config/config.go) | Go | -45 | 0 | -10 | -55 |
| [IBC-AGENT/cluster-manager/scripts/config.yaml](/IBC-AGENT/cluster-manager/scripts/config.yaml) | YAML | -19 | -1 | -4 | -24 |
| [IBC-AGENT/cluster-manager/temp/docker-compose.yml](/IBC-AGENT/cluster-manager/temp/docker-compose.yml) | YAML | -19 | 0 | -5 | -24 |
| [IBC-BACKEND/docker-compose.yml](/IBC-BACKEND/docker-compose.yml) | YAML | 19 | 0 | 2 | 21 |
| [IBC-BACKEND/instance\_create\_response.json](/IBC-BACKEND/instance_create_response.json) | JSONC | 1 | 0 | 0 | 1 |
| [IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/bpmnChoreography.go](/IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/bpmnChoreography.go) | Go | 15 | 0 | 6 | 21 |
| [IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/go.mod](/IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/go.mod) | Go Module File | 13 | 0 | 5 | 18 |
| [IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/go.sum](/IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/go.sum) | Go Checksum File | 156 | 0 | 1 | 157 |
| [IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/test.fabric](/IBC-BACKEND/opt/chaincode-go-bpmn/chaincode-go-bpmn/test.fabric) | JSONC | 19 | 0 | 1 | 20 |
| [IBC-BACKEND/opt/config/ccp\_template.yaml](/IBC-BACKEND/opt/config/ccp_template.yaml) | YAML | 63 | 0 | 0 | 63 |
| [IBC-BACKEND/opt/config/configtx.yaml](/IBC-BACKEND/opt/config/configtx.yaml) | YAML | 269 | 267 | 73 | 609 |
| [IBC-BACKEND/opt/config/core.yaml](/IBC-BACKEND/opt/config/core.yaml) | YAML | 237 | 455 | 73 | 765 |
| [IBC-BACKEND/opt/config/manifest.json](/IBC-BACKEND/opt/config/manifest.json) | JSONC | 64 | 0 | 0 | 64 |
| [IBC-BACKEND/opt/config/msp\_config\_template.yaml](/IBC-BACKEND/opt/config/msp_config_template.yaml) | YAML | 14 | 0 | 1 | 15 |
| [IBC-BACKEND/opt/config/orderer.yaml](/IBC-BACKEND/opt/config/orderer.yaml) | YAML | 105 | 219 | 47 | 371 |
| [IBC-BACKEND/opt/firefly-go/chaincode/contract.go](/IBC-BACKEND/opt/firefly-go/chaincode/contract.go) | Go | 92 | 0 | 8 | 100 |
| [IBC-BACKEND/opt/firefly-go/chaincode/contract\_test.go](/IBC-BACKEND/opt/firefly-go/chaincode/contract_test.go) | Go | 36 | 0 | 9 | 45 |
| [IBC-BACKEND/opt/firefly-go/chaincode/mocks/chaincodestub.go](/IBC-BACKEND/opt/firefly-go/chaincode/mocks/chaincodestub.go) | Go | 2,700 | 0 | 216 | 2,916 |
| [IBC-BACKEND/opt/firefly-go/chaincode/mocks/clientidentity.go](/IBC-BACKEND/opt/firefly-go/chaincode/mocks/clientidentity.go) | Go | 373 | 0 | 32 | 405 |
| [IBC-BACKEND/opt/firefly-go/chaincode/mocks/statequeryiterator.go](/IBC-BACKEND/opt/firefly-go/chaincode/mocks/statequeryiterator.go) | Go | 215 | 0 | 21 | 236 |
| [IBC-BACKEND/opt/firefly-go/chaincode/mocks/transaction.go](/IBC-BACKEND/opt/firefly-go/chaincode/mocks/transaction.go) | Go | 151 | 0 | 16 | 167 |
| [IBC-BACKEND/opt/firefly-go/firefly.go](/IBC-BACKEND/opt/firefly-go/firefly.go) | Go | 18 | 0 | 6 | 24 |
| [IBC-BACKEND/opt/firefly-go/go.mod](/IBC-BACKEND/opt/firefly-go/go.mod) | Go Module File | 35 | 0 | 4 | 39 |
| [IBC-BACKEND/opt/firefly-go/go.sum](/IBC-BACKEND/opt/firefly-go/go.sum) | Go Checksum File | 167 | 0 | 1 | 168 |
| [IBC-BACKEND/opt/oracle-go/go.mod](/IBC-BACKEND/opt/oracle-go/go.mod) | Go Module File | 6 | 1 | 3 | 10 |
| [IBC-BACKEND/opt/oracle-go/go.sum](/IBC-BACKEND/opt/oracle-go/go.sum) | Go Checksum File | 154 | 0 | 1 | 155 |
| [IBC-BACKEND/opt/oracle-go/oracle/oracle.go](/IBC-BACKEND/opt/oracle-go/oracle/oracle.go) | Go | 104 | 0 | 29 | 133 |
| [IBC-BACKEND/opt/oracle-go/oracle/oracle\_client.go](/IBC-BACKEND/opt/oracle-go/oracle/oracle_client.go) | Go | 26 | 0 | 5 | 31 |
| [IBC-BACKEND/opt/oracle-go/oracle\_stub.go](/IBC-BACKEND/opt/oracle-go/oracle_stub.go) | Go | 17 | 0 | 5 | 22 |
| [IBC-BACKEND/opt/oracleFFI.json](/IBC-BACKEND/opt/oracleFFI.json) | JSONC | 40 | 0 | 0 | 40 |
| [IBC-BACKEND/opt/stateCharts-go/go.mod](/IBC-BACKEND/opt/stateCharts-go/go.mod) | Go Module File | 3 | 0 | 3 | 6 |
| [IBC-BACKEND/opt/stateCharts-go/go.sum](/IBC-BACKEND/opt/stateCharts-go/go.sum) | Go Checksum File | 2,110 | 0 | 1 | 2,111 |
| [IBC-BACKEND/opt/stateCharts-go/stateCharts/stateCharts\_client.go](/IBC-BACKEND/opt/stateCharts-go/stateCharts/stateCharts_client.go) | Go | 37 | 0 | 11 | 48 |
| [IBC-BACKEND/opt/stateCharts-go/stateCharts\_stub.go](/IBC-BACKEND/opt/stateCharts-go/stateCharts_stub.go) | Go | 17 | 0 | 5 | 22 |
| [IBC-BACKEND/opt/statechartFFI.json](/IBC-BACKEND/opt/statechartFFI.json) | JSONC | 60 | 0 | 0 | 60 |
| [IBC-BACKEND/opt/statecharts-javascript-2.2/package.json](/IBC-BACKEND/opt/statecharts-javascript-2.2/package.json) | JSONC | 50 | 0 | 1 | 51 |
| [IBC-BACKEND/requirements.txt](/IBC-BACKEND/requirements.txt) | pip requirements | 75 | 0 | 0 | 75 |

[Summary](results.md) / [Details](details.md) / [Diff Summary](diff.md) / Diff Details