package task

import (
	"cluster-manager/internal/cluster/ipfscluster"
	"cluster-manager/internal/infra"
	"cluster-manager/internal/models"
	"cluster-manager/internal/provider"
	"cluster-manager/internal/repository"
	"encoding/json"
	"fmt"
)

// 注册
func initIPFS() {
	RegisterExecHandler("ipfs", "create", handleIPFSCreate, assertIPFSCreateConfig)
	RegisterExecHandler("ipfs", "remove", handleIPFSRemove, assertIPFSRemoveConfig)
	RegisterPostHandler("ipfs", "create", handleIPFSPostCreate, assertIPFSCreateResponse)
	RegisterPostHandler("ipfs", "remove", handleIPFSPostRemove, assertIPFSRemoveResponse)
}

func handleIPFSCreate(raw json.RawMessage, prov provider.Provider) (any, error) {
	cfgAny, err := assertIPFSCreateConfig(raw)
	if err != nil {
		return nil, err
	}
	cfg := cfgAny.(ipfscluster.IPFSCreateConfig)

	return ipfscluster.BuildIPFS(cfg, prov)
}

func handleIPFSRemove(raw json.RawMessage, prov provider.Provider) (any, error) {
	cfgAny, err := assertIPFSRemoveConfig(raw)
	if err != nil {
		return nil, err
	}
	cfg := cfgAny.(ipfscluster.IPFSRemoveConfig)
	return nil, ipfscluster.RemoveIPFS(cfg, prov)
}

func assertIPFSCreateConfig(raw json.RawMessage) (interface{}, error) {
	var cfg ipfscluster.IPFSCreateConfig
	if err := json.Unmarshal(raw, &cfg); err != nil {
		return nil, err
	}
	return cfg, nil
}

func assertIPFSRemoveConfig(raw json.RawMessage) (interface{}, error) {
	var cfg ipfscluster.IPFSRemoveConfig
	if err := json.Unmarshal(raw, &cfg); err != nil {
		return nil, err
	}
	return cfg, nil
}

func handleIPFSPostCreate(taskRecord *models.Task, result any, prov provider.Provider) error {
	res, ok := result.(ipfscluster.IPFSCreateResponse)
	if !ok {
		return fmt.Errorf("invalid result type for IPFS create")
	}

	clusterManager := &repository.ClusterManager{DB: infra.DB}
	cluster := &models.Cluster{
		ClusterID:  res.ClusterID,
		ProviderID: taskRecord.ProviderID,
		Type:       taskRecord.Type,
	}

	if err := clusterManager.CreateCluster(cluster); err != nil {
		return fmt.Errorf("failed to create cluster in database: %w", err)
	}

	taskManager := &repository.TaskManager{DB: infra.DB}
	clusterID := res.ClusterID
	if err := taskManager.UpdateTaskStatus(taskRecord.ID, "success", &clusterID, "IPFS cluster created"); err != nil {
		return fmt.Errorf("failed to update task status: %w", err)
	}

	// 更新task关联的clusterID
	if err := taskManager.UpdateTaskClusterID(taskRecord.ID, clusterID); err != nil {
		return fmt.Errorf("failed to update task cluster ID: %w", err)
	}

	return nil
}

func handleIPFSPostRemove(taskRecord *models.Task, result any, prov provider.Provider) error {
	var taskManager = &repository.TaskManager{DB: infra.DB}
	return taskManager.UpdateTaskStatus(taskRecord.ID, "completed", nil, "IPFS cluster removed")
}

func assertIPFSCreateResponse(result any) (interface{}, error) {
	res, ok := result.(ipfscluster.IPFSCreateResponse)
	if !ok {
		return nil, fmt.Errorf("invalid result type for IPFS create")
	}
	return res, nil
}

func assertIPFSRemoveResponse(result any) (interface{}, error) {
	_, ok := result.(ipfscluster.IPFSRemoveResponse)
	if !ok {
		return nil, fmt.Errorf("invalid result type for IPFS remove")
	}
	return nil, nil
}
