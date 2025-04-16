package task

import (
	"context"
	"log"
	"time"

	"cluster-manager/internal/infra"

	"github.com/panjf2000/ants/v2"
)

var taskPool *ants.Pool

func StartTaskWorker(ctx context.Context) {
	var err error
	taskPool, err = ants.NewPool(10) // 设置最大并发数
	if err != nil {
		log.Fatalf("Failed to create ants pool: %v", err)
	}

	log.Println("🐜 Ants pool started")

	go func() {
		for {
			select {
			case <-ctx.Done():
				log.Println("🛑 Task worker stopped")
				return
			default:
				fetchAndDispatch()
				time.Sleep(2 * time.Second)
			}
		}
	}()
}

// 从 Redis 拉取任务并提交给 ants
func fetchAndDispatch() {
	taskData, err := infra.Rdb.LPop(context.Background(), "task_queue").Result()
	if err != nil || taskData == "" {
		return
	}
	// 将任务扔给 ants
	_ = taskPool.Submit(func() {
		if err := HandleTask(taskData); err != nil {
			log.Printf("❌ Task failed: %v", err)
		}
	})
}
