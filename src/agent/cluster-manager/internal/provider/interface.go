package provider

import (
	"cluster-manager/internal/models"
	"fmt"
	"time"
)

type Provider interface {
	ID() string
	Type() string // docker / k8s / vm / bare-metal

	DeployProgram(spec ProgramSpec) (ProgramStatus, error)
	StopProgram(programID string) error
	UpdateProgram(spec ProgramSpec) (ProgramStatus, error)
	GetStatus(programID string) (ProgramStatus, error)
	GetProvider(provider models.Provider) (*Provider, error)

	ListProgramsByLabel(key, value string) ([]ProgramStatus, error)
	GetClusterStatus(clusterID string) (map[string]ProgramStatus, error)
}

type ProgramSpec struct {
	ID         string            // 全局唯一ID，可自动生成
	Name       string            // 逻辑名称，如 "ipfs-node-1"
	Command    string            // 可执行程序或主命令，如 ipfs、minio、fabric
	Args       []string          // 命令行参数
	Env        map[string]string // 环境变量
	Resources  map[string]string // CPU、内存等资源限制
	Network    string            // 网络标识，供Provider解析
	Volumes    map[string]string // 本地路径 -> 挂载路径
	Labels     map[string]string // 标签，辅助调度
	ReplicaIdx int               // 副本编号（可选）
}

type ProgramStatus struct {
	ID      string
	Name    string
	Status  string // running, stopped, error, unknown
	Message string // 错误信息或状态说明
	Created time.Time
}

func InstantiateProvider(record *models.Provider) (Provider, error) {
	switch record.Type {
	case "docker":
		dockerProvider, err := NewDockerProvider(*record)
		if err != nil {
			return nil, fmt.Errorf("failed to create Docker provider: %w", err)
		}
		return dockerProvider, nil
	case "k8s":
		// return k8s.NewK8sProvider(*record), nil Future work
		return nil, fmt.Errorf("k8s provider not implemented yet")
	default:
		return nil, fmt.Errorf("unsupported provider type: %s", record.Type)
	}
}
