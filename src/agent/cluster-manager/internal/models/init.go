package models

import (
	"fmt"

	"gorm.io/gorm"
)

var Models = []interface{}{
	&Cluster{},
	&Task{},
	&Provider{}, // 添加 Provider 模型
}

// RegisterModels 自动迁移所有模型，并返回迁移结果
func RegisterModels(db *gorm.DB) error {
	for _, model := range Models {
		err := db.AutoMigrate(model)
		if err != nil {
			return fmt.Errorf("AutoMigrate failed for model %T: %v", model, err)
		}
	}
	return nil
}
