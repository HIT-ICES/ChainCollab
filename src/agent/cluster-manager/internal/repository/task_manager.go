// task/task_manager.go
package repository

import (
	"cluster-manager/internal/models"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"gorm.io/gorm"
)

// TaskManager 负责处理任务相关操作
type TaskManager struct {
	DB *gorm.DB
}

// CreateTask 保存任务到数据库
func (manager *TaskManager) CreateTask(task *models.Task) error {
	// 将任务信息保存到数据库
	if err := manager.DB.Create(task).Error; err != nil {
		return fmt.Errorf("failed to create task: %w", err)
	}
	return nil
}

// GetTaskByID 根据任务ID查询任务
func (manager *TaskManager) GetTaskByID(taskID string) (*models.Task, error) {
	var task models.Task
	// 使用 taskID 查询任务
	if err := manager.DB.Where("id = ?", taskID).First(&task).Error; err != nil {
		// 如果找不到任务，则返回自定义错误
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, fmt.Errorf("task with ID %s not found", taskID)
		}
		// 其他数据库错误
		return nil, fmt.Errorf("failed to retrieve task: %w", err)
	}
	return &task, nil
}

// ListTasks 列出所有任务
func (manager *TaskManager) ListTasks() ([]models.Task, error) {
	var tasks []models.Task
	// 获取所有任务
	if err := manager.DB.Find(&tasks).Error; err != nil {
		return nil, fmt.Errorf("failed to list tasks: %w", err)
	}
	return tasks, nil
}

func (tm *TaskManager) UpdateTaskStatus(
	taskID string,
	status string,
	result any,
	errorMsg string,
) error {
	updates := map[string]interface{}{
		"status":     status,
		"updated_at": time.Now(),
		"error_msg":  errorMsg,
	}

	if result != nil {
		encoded, err := json.Marshal(result)
		if err != nil {
			return err
		}
		updates["result"] = encoded
	}

	// 成功或失败则标记完成时间
	if status == "success" || status == "failed" {
		updates["finished_at"] = time.Now()
	}

	return tm.DB.Model(&models.Task{}).Where("id = ?", taskID).Updates(updates).Error
}

func (m *TaskManager) UpdateTaskClusterID(taskID, clusterID string) error {
	return m.DB.Model(&models.Task{}).
		Where("id = ?", taskID).
		Update("cluster_id", clusterID).
		Error
}
