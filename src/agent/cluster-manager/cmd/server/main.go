package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"cluster-manager/internal/api"
	"cluster-manager/internal/infra"
	"cluster-manager/internal/task"

	"github.com/gin-gonic/gin"
	"github.com/spf13/viper"
)

func main() {

	if err := InitConfig("config.yml"); err != nil {
		log.Fatalf("❌ Config init failed: %v", err)
	}

	// 初始化基础设施(全局唯一连接：MySQL、Redis、Logger)
	if err := infra.InitInfra(); err != nil {
		log.Fatalf("❌ Infra init failed: %v", err)
	}

	// 初始化TaskHandler
	task.InitTaskHandler()

	task.StartTaskWorker(context.Background(), viper.GetInt("workers.worker_count"))

	r := gin.Default()
	api.RegisterRoutes(r, infra.GetDB(), infra.GetMQ())

	// 启动 HTTP Server
	srv := &http.Server{
		Addr:    ":8080",
		Handler: r,
	}

	go func() {
		log.Println("🚀 HTTP server listening on :8080")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("❌ HTTP server error: %s\n", err)
		}
	}()

	// 优雅退出
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("🛑 Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("❌ Server forced to shutdown: %v", err)
	}

	log.Println("✅ Server exited gracefully")
}

func InitConfig(configPath string) error {
	viper.SetConfigFile(configPath)
	err := viper.ReadInConfig()
	if err != nil {
		return err
	}
	log.Println("✅ Config loaded from", configPath)
	log.Println("Config:", viper.AllSettings())
	return nil
}
