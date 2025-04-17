package task

import (
	"cluster-manager/internal/infra"
	"cluster-manager/internal/infra/mq"
	"context"
	"log"
	"time"

	"github.com/panjf2000/ants/v2"
)

var taskPool *ants.Pool

func StartTaskWorker(ctx context.Context, workerCount int) {
	var err error
	taskPool, err = ants.NewPool(workerCount)
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
				fetchAndDispatch(infra.GetMQ())
				time.Sleep(2 * time.Second)
			}
		}
	}()
}

func fetchAndDispatch(mq mq.MQ) {
	ctx := context.Background()

	messages, err := mq.Consume(ctx)
	if err != nil {
		// log.Printf("⚠️ Failed to consume from MQ: %v", err)
		return
	}

	for _, msg := range messages {
		msgCopy := msg
		_ = taskPool.Submit(func() {
			if err := HandleTask(string(msgCopy.Payload)); err != nil {
				log.Printf("❌ Task failed: %v", err)
			} else {
				if err := mq.Ack(ctx, msgCopy.ID); err != nil {
					log.Printf("⚠️ Failed to ack message %s: %v", msgCopy.ID, err)
				}
			}
		})
	}
}
