package models

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type Task struct {
	ID         string          `gorm:"type:char(100);primaryKey"` // UUID 主键
	TaskName   string          `gorm:"not null"`                  // 可选任务名，方便识别
	Type       string          `gorm:"not null"`                  // ipfs, minio, fabric 等
	Action     string          `gorm:"not null"`                  // create, delete, update
	ProviderID string          `gorm:"not null"`                  // 指向资源提供者（docker、k8s等）的ID
	ClusterID  string          `json:"cluster_id"`                // 关联的集群ID
	Config     json.RawMessage `gorm:"type:json" json:"config"`   // 延迟解析配置
	Status     string          `gorm:"default:'pending'"`         // 任务状态：pending, running, success, failed
	Result     json.RawMessage `gorm:"type:json"`                 // 返回结果
	ErrorMsg   string          `gorm:"type:text"`                 // 错误信息
	CreatedAt  time.Time       `gorm:"autoCreateTime"`            // 创建时间
	UpdatedAt  time.Time       `gorm:"autoUpdateTime"`            // 更新时间
	FinishedAt *time.Time      // 结束时间，可为 null
}

func (t *Task) BeforeCreate(tx *gorm.DB) (err error) {
	if t.ID == "" {
		t.ID = "task-" + uuid.New().String() // 自动生成 UUID
	}
	return nil
}
