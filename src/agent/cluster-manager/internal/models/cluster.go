package models

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// Cluster 模型表示集群信息
type Cluster struct {
	ID         string `gorm:"type:char(100);primaryKey"`     // 内部ID，数据库主键
	ClusterID  string `gorm:"type:varchar(191);uniqueIndex"` // 外部集群标识符，唯一标识集群
	ProviderID string `gorm:"not null"`                      // 关联的资源提供者 ID
	Type       string `gorm:"not null"`                      // 集群类型，如 ipfs, minio, fabric 等
	CreatedAt  time.Time
	UpdatedAt  time.Time
}

func (c *Cluster) BeforeCreate(tx *gorm.DB) (err error) {
	if c.ID == "" {
		c.ID = "cluster-" + uuid.New().String()
	}

	return nil
}
