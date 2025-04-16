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
)

func main() {
	// 初始化基础设施(全局唯一连接：MySQL、Redis、Logger)
	if err := infra.InitInfra("config.yml"); err != nil {
		log.Fatalf("❌ Infra init failed: %v", err)
	}

	// 初始化TaskHandler
	task.InitTaskHandler()

	task.StartTaskWorker(context.Background())

	r := gin.Default()
	api.RegisterRoutes(r, infra.DB, infra.Rdb)

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
