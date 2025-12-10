# Details

Date : 2025-04-13 02:26:23

Directory /home/logres/system/src/agent/cluster-manager

Total : 34 files,  1250 codes, 1 comments, 196 blanks, all 1447 lines

[Summary](results.md) / Details / [Diff Summary](diff.md) / [Diff Details](diff-details.md)

## Files
| filename | language | code | comment | blank | total |
| :--- | :--- | ---: | ---: | ---: | ---: |
| [IBC-AGENT/cluster-manager/build/docker-compose-template.yml](/IBC-AGENT/cluster-manager/build/docker-compose-template.yml) | YAML | 33 | 0 | 5 | 38 |
| [IBC-AGENT/cluster-manager/cmd/server/main.go](/IBC-AGENT/cluster-manager/cmd/server/main.go) | Go | 47 | 0 | 12 | 59 |
| [IBC-AGENT/cluster-manager/config.yml](/IBC-AGENT/cluster-manager/config.yml) | YAML | 18 | 0 | 1 | 19 |
| [IBC-AGENT/cluster-manager/go.mod](/IBC-AGENT/cluster-manager/go.mod) | Go Module File | 79 | 0 | 4 | 83 |
| [IBC-AGENT/cluster-manager/go.sum](/IBC-AGENT/cluster-manager/go.sum) | Go Checksum File | 277 | 0 | 1 | 278 |
| [IBC-AGENT/cluster-manager/internal/api/router.go](/IBC-AGENT/cluster-manager/internal/api/router.go) | Go | 86 | 0 | 17 | 103 |
| [IBC-AGENT/cluster-manager/internal/cluster/interface.go](/IBC-AGENT/cluster-manager/internal/cluster/interface.go) | Go | 5 | 0 | 3 | 8 |
| [IBC-AGENT/cluster-manager/internal/cluster/ipfscluster/ipfs-cluster.go](/IBC-AGENT/cluster-manager/internal/cluster/ipfscluster/ipfs-cluster.go) | Go | 67 | 0 | 12 | 79 |
| [IBC-AGENT/cluster-manager/internal/cluster/ipfscluster/types.go](/IBC-AGENT/cluster-manager/internal/cluster/ipfscluster/types.go) | Go | 0 | 0 | 1 | 1 |
| [IBC-AGENT/cluster-manager/internal/infra/config.go](/IBC-AGENT/cluster-manager/internal/infra/config.go) | Go | 14 | 0 | 4 | 18 |
| [IBC-AGENT/cluster-manager/internal/infra/logger.go](/IBC-AGENT/cluster-manager/internal/infra/logger.go) | Go | 14 | 0 | 4 | 18 |
| [IBC-AGENT/cluster-manager/internal/infra/mysql.go](/IBC-AGENT/cluster-manager/internal/infra/mysql.go) | Go | 16 | 0 | 5 | 21 |
| [IBC-AGENT/cluster-manager/internal/infra/redis.go](/IBC-AGENT/cluster-manager/internal/infra/redis.go) | Go | 20 | 0 | 6 | 26 |
| [IBC-AGENT/cluster-manager/internal/infra/registry.go](/IBC-AGENT/cluster-manager/internal/infra/registry.go) | Go | 24 | 0 | 8 | 32 |
| [IBC-AGENT/cluster-manager/internal/models/cluster.go](/IBC-AGENT/cluster-manager/internal/models/cluster.go) | Go | 38 | 0 | 7 | 45 |
| [IBC-AGENT/cluster-manager/internal/models/cluster\_node.go](/IBC-AGENT/cluster-manager/internal/models/cluster_node.go) | Go | 16 | 0 | 3 | 19 |
| [IBC-AGENT/cluster-manager/internal/models/init.go](/IBC-AGENT/cluster-manager/internal/models/init.go) | Go | 13 | 0 | 4 | 17 |
| [IBC-AGENT/cluster-manager/internal/models/provider.go](/IBC-AGENT/cluster-manager/internal/models/provider.go) | Go | 11 | 0 | 3 | 14 |
| [IBC-AGENT/cluster-manager/internal/models/task.go](/IBC-AGENT/cluster-manager/internal/models/task.go) | Go | 20 | 0 | 3 | 23 |
| [IBC-AGENT/cluster-manager/internal/provider/docker/client.go](/IBC-AGENT/cluster-manager/internal/provider/docker/client.go) | Go | 16 | 0 | 4 | 20 |
| [IBC-AGENT/cluster-manager/internal/provider/docker/container.go](/IBC-AGENT/cluster-manager/internal/provider/docker/container.go) | Go | 37 | 0 | 7 | 44 |
| [IBC-AGENT/cluster-manager/internal/provider/docker/network.go](/IBC-AGENT/cluster-manager/internal/provider/docker/network.go) | Go | 35 | 0 | 7 | 42 |
| [IBC-AGENT/cluster-manager/internal/provider/docker/types.go](/IBC-AGENT/cluster-manager/internal/provider/docker/types.go) | Go | 8 | 0 | 2 | 10 |
| [IBC-AGENT/cluster-manager/internal/provider/interface.go](/IBC-AGENT/cluster-manager/internal/provider/interface.go) | Go | 6 | 0 | 3 | 9 |
| [IBC-AGENT/cluster-manager/internal/repository/cluster\_manager.go](/IBC-AGENT/cluster-manager/internal/repository/cluster_manager.go) | Go | 41 | 0 | 8 | 49 |
| [IBC-AGENT/cluster-manager/internal/repository/cluster\_node\_manager.go](/IBC-AGENT/cluster-manager/internal/repository/cluster_node_manager.go) | Go | 41 | 0 | 8 | 49 |
| [IBC-AGENT/cluster-manager/internal/repository/provider\_manager.go](/IBC-AGENT/cluster-manager/internal/repository/provider_manager.go) | Go | 34 | 0 | 7 | 41 |
| [IBC-AGENT/cluster-manager/internal/repository/task\_manager.go](/IBC-AGENT/cluster-manager/internal/repository/task_manager.go) | Go | 41 | 0 | 7 | 48 |
| [IBC-AGENT/cluster-manager/internal/task/handler.go](/IBC-AGENT/cluster-manager/internal/task/handler.go) | Go | 43 | 0 | 6 | 49 |
| [IBC-AGENT/cluster-manager/internal/task/types.go](/IBC-AGENT/cluster-manager/internal/task/types.go) | Go | 25 | 0 | 5 | 30 |
| [IBC-AGENT/cluster-manager/internal/task/worker.go](/IBC-AGENT/cluster-manager/internal/task/worker.go) | Go | 42 | 0 | 10 | 52 |
| [IBC-AGENT/cluster-manager/pkg/config/config.go](/IBC-AGENT/cluster-manager/pkg/config/config.go) | Go | 45 | 0 | 10 | 55 |
| [IBC-AGENT/cluster-manager/scripts/config.yaml](/IBC-AGENT/cluster-manager/scripts/config.yaml) | YAML | 19 | 1 | 4 | 24 |
| [IBC-AGENT/cluster-manager/temp/docker-compose.yml](/IBC-AGENT/cluster-manager/temp/docker-compose.yml) | YAML | 19 | 0 | 5 | 24 |

[Summary](results.md) / Details / [Diff Summary](diff.md) / [Diff Details](diff-details.md)