package task

import "encoding/json"

type Task struct {
	Type       string          `json:"type"`        // ipfs, minio, fabric, etc.
	Action     string          `json:"action"`      // create, delete, update
	ProviderID string          `json:"provider_id"` // 指向 docker 主机或 K8s 配置
	Config     json.RawMessage `json:"config"`      // 延迟解析，按类型再处理
}
