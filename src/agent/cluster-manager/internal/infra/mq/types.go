package mq

import (
	"context"
	"errors"
	"fmt"
)

type Message struct {
	ID      string
	Payload []byte
}
type MQ interface {
	Publish(ctx context.Context, payload []byte) error
	Consume(ctx context.Context) ([]Message, error)
	Ack(ctx context.Context, msgID string) error
}

type MQType string

const (
	MQRedis MQType = "redis"
	MQKafka MQType = "kafka"
)

type MQConfig struct {
	Type  MQType       `mapstructure:"type"`
	Redis *RedisConfig `mapstructure:"redis"`
	Kafka *KafkaConfig `mapstructure:"kafka"`
	// To Expand
}

type RedisConfig struct {
	Addr       string `mapstructure:"addr"`
	Password   string `mapstructure:"password"`
	DB         int    `mapstructure:"db"`
	Stream     string `mapstructure:"stream"`      // Redis Stream 名称
	Group      string `mapstructure:"group"`       // 消费组名称
	ConsumerID string `mapstructure:"consumer_id"` // 当前消费者 ID
}

type KafkaConfig struct {
	Brokers  []string `mapstructure:"brokers"`
	Topic    string   `mapstructure:"topic"`
	GroupID  string   `mapstructure:"group_id"`
	ClientID string   `mapstructure:"client_id"`
}

func InitMQ(ctx context.Context, cfg MQConfig) (MQ, error) {
	switch cfg.Type {
	case MQRedis:
		if cfg.Redis == nil {
			return nil, errors.New("redis config is required")
		}
		return NewRedisMQ(ctx, *cfg.Redis)

	case MQKafka:
		if cfg.Kafka == nil {
			return nil, errors.New("kafka config is required")
		}
		// return NewKafkaMQ(ctx, *cfg.Kafka) // TODO: 实现 Kafka 支持
		return nil, errors.New("kafka support not implemented yet")

	default:
		return nil, fmt.Errorf("unsupported mq type: %s", cfg.Type)
	}
}
