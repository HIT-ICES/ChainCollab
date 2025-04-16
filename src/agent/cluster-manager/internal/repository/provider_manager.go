// internal/service/provider_manager.go
package repository

import (
	"cluster-manager/internal/models"
	"fmt"

	"gorm.io/gorm"
)

// ProviderManager 负责管理资源提供者相关操作
type ProviderManager struct {
	DB *gorm.DB
}

// RegisterProvider 将一个新的资源提供者保存到数据库
func (manager *ProviderManager) RegisterProvider(provider *models.Provider) error {
	if err := manager.DB.Create(provider).Error; err != nil {
		return fmt.Errorf("failed to register provider: %w", err)
	}
	return nil
}

// GetProvider 根据ID获取资源提供者
func (manager *ProviderManager) GetProvider(providerID string) (*models.Provider, error) {
	fmt.Println(providerID)
	var provider models.Provider
	if err := manager.DB.First(&provider, "id = ?", providerID).Error; err != nil {
		return nil, fmt.Errorf("failed to get provider: %w", err)
	}
	return &provider, nil
}

// ListProviders 列出所有资源提供者
func (manager *ProviderManager) ListProviders() ([]models.Provider, error) {
	var providers []models.Provider
	if err := manager.DB.Find(&providers).Error; err != nil {
		return nil, fmt.Errorf("failed to list providers: %w", err)
	}
	return providers, nil
}
