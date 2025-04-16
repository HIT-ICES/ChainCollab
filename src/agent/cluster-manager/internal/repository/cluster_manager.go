// internal/service/cluster_manager.go
package repository

import (
	"cluster-manager/internal/models"
	"fmt"

	"gorm.io/gorm"
)

type ClusterManager struct {
	DB *gorm.DB
}

func (m *ClusterManager) CreateCluster(cluster *models.Cluster) error {
	return m.DB.Create(cluster).Error
}

func (m *ClusterManager) RemoveCluster(clusterID string) error {
	var cluster models.Cluster
	if err := m.DB.First(&cluster, "id = ?", clusterID).Error; err != nil {
		return fmt.Errorf("find cluster failed: %w", err)
	}
	return m.DB.Delete(&cluster).Error
}

func (m *ClusterManager) ListClusters() ([]models.Cluster, error) {
	var clusters []models.Cluster
	err := m.DB.Find(&clusters).Error
	return clusters, err
}

func (m *ClusterManager) GetClusterByClusterID(clusterID string) (*models.Cluster, error) {
	var cluster models.Cluster
	if err := m.DB.First(&cluster, "cluster_id = ?", clusterID).Error; err != nil {
		return nil, fmt.Errorf("failed to find cluster with ClusterID %s: %w", clusterID, err)
	}
	return &cluster, nil
}
