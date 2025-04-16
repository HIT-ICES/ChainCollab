package ipfscluster

import (
	"cluster-manager/internal/provider"
	"cluster-manager/internal/utils"
	"fmt"
)

type IPFSCreateConfig struct {
	ClusterID   string            `json:"cluster_id"`   // 可选，自动生成
	ClusterSize int               `json:"cluster_size"` // 必填
	Network     string            `json:"network"`      // 可选
	BaseVolume  string            `json:"base_volume"`  // 可选，不填代表无需挂载
	Labels      map[string]string `json:"labels"`       // 可选
}

type IPFSCreateResponse struct {
	ClusterID string `json:"cluster_id"`
}

type IPFSRemoveConfig struct {
	ClusterID string `json:"cluster_id"`
}

type IPFSRemoveResponse struct {
	ClusterID string `json:"cluster_id"`
}

type ClusterStatusConfig struct {
	ClusterID string `json:"cluster_id"`
}

type ClusterStatusResponse struct {
	ClusterID string                   `json:"cluster_id"`
	Total     int                      `json:"total"`
	Running   int                      `json:"running"`
	Failed    int                      `json:"failed"`
	Replicas  []provider.ProgramStatus `json:"replicas"`
}

func BuildIPFS(cfg IPFSCreateConfig, prov provider.Provider) (IPFSCreateResponse, error) {
	var resp IPFSCreateResponse
	resp.ClusterID = cfg.ClusterID

	if cfg.Network == "" {
		cfg.Network = fmt.Sprintf("ipfs-net-%s", utils.RandomShortID())
	}

	useVolume := true
	if cfg.BaseVolume == "" {
		useVolume = false
		cfg.BaseVolume = "/tmp" // 占位，不使用
	}

	if cfg.Labels == nil {
		cfg.Labels = make(map[string]string)
	}
	if cfg.ClusterID == "" {
		cfg.ClusterID = fmt.Sprintf("ipfs-cluster-%s", utils.RandomShortID())
	}
	cfg.Labels["cluster_id"] = cfg.ClusterID

	for i := 0; i < cfg.ClusterSize; i++ {
		id := fmt.Sprintf("%s-%d", cfg.ClusterID, i)

		vols := map[string]string{}
		if useVolume {
			hostVol := fmt.Sprintf("%s/%s-%d", cfg.BaseVolume, cfg.ClusterID, i)
			vols[hostVol] = "/data/ipfs"
		}

		spec := provider.ProgramSpec{
			ID:         id,
			Name:       id,
			Command:    "ipfs/go-ipfs",
			Args:       []string{"daemon"},
			Env:        map[string]string{"IPFS_PROFILE": "server"},
			Network:    cfg.Network,
			Volumes:    vols,
			Labels:     cfg.Labels,
			ReplicaIdx: i,
		}

		_, err := prov.DeployProgram(spec)
		if err != nil {
			return resp, fmt.Errorf("failed to deploy replica %d: %w", i, err)
		}
	}

	resp.ClusterID = cfg.ClusterID
	return resp, nil
}

func RemoveIPFS(cfg IPFSRemoveConfig, prov provider.Provider) error {
	replicas, err := prov.ListProgramsByLabel("cluster_id", cfg.ClusterID)
	if err != nil {
		return fmt.Errorf("failed to list programs for cluster %s: %w", cfg.ClusterID, err)
	}

	for _, replica := range replicas {
		if err := prov.StopProgram(replica.ID); err != nil {
			return fmt.Errorf("failed to stop program %s: %w", replica.ID, err)
		}
	}

	return nil
}

func GetClusterStatus(clusterID string, prov provider.Provider) (*ClusterStatusResponse, error) {
	replicas, err := prov.ListProgramsByLabel("cluster_id", clusterID)
	if err != nil {
		return nil, fmt.Errorf("failed to list programs for cluster %s: %w", clusterID, err)
	}

	var running, failed int
	for _, r := range replicas {
		switch r.Status {
		case "running":
			running++
		default:
			failed++
		}
	}

	return &ClusterStatusResponse{
		ClusterID: clusterID,
		Total:     len(replicas),
		Running:   running,
		Failed:    failed,
		Replicas:  replicas,
	}, nil
}
