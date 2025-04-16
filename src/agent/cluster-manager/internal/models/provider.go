// models/provider.go
package models

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type Provider struct {
	ID        string `gorm:"type:char(100);primaryKey"`
	Type      string
	Host      string
	Port      int
	CreatedAt time.Time
	UpdatedAt time.Time
}

func (p *Provider) BeforeCreate(tx *gorm.DB) (err error) {
	if p.ID == "" {
		p.ID = "provider-" + uuid.New().String()
	}
	return
}
