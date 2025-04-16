package infra

import (
	"context"
	"log"

	"github.com/redis/go-redis/v9"
)

var Rdb *redis.Client

func InitRedis(addr, password string, db int) error {
	Rdb = redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: password,
		DB:       db,
	})

	_, err := Rdb.Ping(context.Background()).Result()
	if err != nil {
		return err
	}
	log.Println("✅ Redis connected")
	return nil
}
