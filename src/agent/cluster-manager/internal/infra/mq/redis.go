package mq

import (
	"context"
	"errors"
	"log"
	"time"

	"github.com/redis/go-redis/v9"
)

type RedisStreamMQ struct {
	client     *redis.Client
	stream     string
	group      string
	consumerID string
}

func NewRedisMQ(ctx context.Context, cfg RedisConfig) (MQ, error) {
	if cfg.Stream == "" || cfg.Group == "" || cfg.ConsumerID == "" {
		return nil, errors.New("redis stream, group and consumer_id must be set")
	}

	client := redis.NewClient(&redis.Options{
		Addr:     cfg.Addr,
		Password: cfg.Password,
		DB:       cfg.DB,
	})

	if err := client.Ping(ctx).Err(); err != nil {
		return nil, err
	}

	log.Println("✅ Redis connected")

	err := client.XGroupCreateMkStream(ctx, cfg.Stream, cfg.Group, "$").Err()
	if err != nil && !isGroupExistsErr(err) {
		return nil, err
	}

	return &RedisStreamMQ{
		client:     client,
		stream:     cfg.Stream,
		group:      cfg.Group,
		consumerID: cfg.ConsumerID,
	}, nil
}

func (r *RedisStreamMQ) Publish(ctx context.Context, payload []byte) error {
	_, err := r.client.XAdd(ctx, &redis.XAddArgs{
		Stream: r.stream,
		Values: map[string]interface{}{
			"data": string(payload),
		},
	}).Result()
	return err
}

func (r *RedisStreamMQ) Consume(ctx context.Context) ([]Message, error) {
	streams, err := r.client.XReadGroup(ctx, &redis.XReadGroupArgs{
		Group:    r.group,
		Consumer: r.consumerID,
		Streams:  []string{r.stream, ">"},
		Count:    10,
		Block:    5 * time.Second,
	}).Result()

	if err != nil || len(streams) == 0 {
		return nil, err
	}

	var result []Message
	for _, msg := range streams[0].Messages {
		data, ok := msg.Values["data"].(string)
		if !ok {
			continue
		}
		result = append(result, Message{
			ID:      msg.ID,
			Payload: []byte(data),
		})
	}
	return result, nil
}

func (r *RedisStreamMQ) Ack(ctx context.Context, msgID string) error {
	return r.client.XAck(ctx, r.stream, r.group, msgID).Err()
}

func isGroupExistsErr(err error) bool {
	return err != nil && (err.Error() == "BUSYGROUP Consumer Group name already exists")
}
