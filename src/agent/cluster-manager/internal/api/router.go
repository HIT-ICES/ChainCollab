package api

import (
	"cluster-manager/internal/models"
	"cluster-manager/internal/provider"
	"cluster-manager/internal/repository"
	"context"
	"encoding/json"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"gorm.io/gorm"
)

func RegisterRoutes(r *gin.Engine, db *gorm.DB, rdb *redis.Client) {
	taskManager := &repository.TaskManager{DB: db}

	r.POST("/tasks", createTaskHandler(taskManager, rdb))
	r.GET("/tasks/:task_id", getTaskHandler(taskManager))
	r.GET("/tasks", listTasksHandler(taskManager))

	providerManager := &repository.ProviderManager{DB: db}

	r.POST("/providers", registerProviderHandler(providerManager))
	r.GET("/providers", listProvidersHandler(providerManager))
	r.GET("/providers/:provider_id", getProviderHandler(providerManager))

	clusterManager := &repository.ClusterManager{DB: db}
	r.GET("/clusters/:cluster_id", getClusterHandler(clusterManager, providerManager))

	r.GET("/ping", pingHandler)
}

func createTaskHandler(taskManager *repository.TaskManager, rdb *redis.Client) gin.HandlerFunc {
	return func(c *gin.Context) {
		var task models.Task
		if err := c.ShouldBindJSON(&task); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid task input"})
			return
		}

		if err := taskManager.CreateTask(&task); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		if err := publishTaskToRedis(rdb, task); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to publish task to Redis"})
			return
		}

		c.JSON(http.StatusCreated, task)
	}
}

func publishTaskToRedis(rdb *redis.Client, task models.Task) error {
	ctx := context.Background()

	taskMessage := map[string]interface{}{
		"task_id": task.ID,
	}
	data, err := json.Marshal(taskMessage)
	if err != nil {
		return err
	}

	return rdb.LPush(ctx, "task_queue", data).Err()
}

func getTaskHandler(taskManager *repository.TaskManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		taskID := c.Param("task_id")

		task, err := taskManager.GetTaskByID(taskID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Task not found"})
			return
		}
		c.JSON(http.StatusOK, task)
	}
}

func listTasksHandler(taskManager *repository.TaskManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		tasks, err := taskManager.ListTasks()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, tasks)
	}
}

func pingHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"message": "pong"})
}

// Provider

func registerProviderHandler(providerManager *repository.ProviderManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		var provider models.Provider
		if err := c.ShouldBindJSON(&provider); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid provider input"})
			return
		}

		if err := providerManager.RegisterProvider(&provider); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusCreated, provider)
	}
}

func listProvidersHandler(providerManager *repository.ProviderManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		providers, err := providerManager.ListProviders()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusOK, providers)
	}
}

func getProviderHandler(providerManager *repository.ProviderManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		providerID := c.Param("provider_id")

		provider, err := providerManager.GetProvider(providerID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Provider not found"})
			return
		}

		c.JSON(http.StatusOK, provider)
	}
}

//CheckCluster

func getClusterHandler(clusterManager *repository.ClusterManager, providerManager *repository.ProviderManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		clusterID := c.Param("cluster_id")

		// 1. 查询集群数据库信息
		cluster, err := clusterManager.GetClusterByClusterID(clusterID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Cluster not found"})
			return
		}

		// 2. 查询 provider 实时状态
		providerRecord, err := providerManager.GetProvider(cluster.ProviderID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get provider"})
			return
		}
		prov, err := provider.InstantiateProvider(providerRecord)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to instantiate provider"})
			return
		}

		// 3. 获取实时状态
		status, err := prov.GetClusterStatus(clusterID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get cluster status"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"cluster": cluster,
			"status":  status,
		})
	}
}
