package infra

import (
	"cluster-manager/internal/infra/db"
	"cluster-manager/internal/infra/logger"
	"cluster-manager/internal/infra/mq"
	"cluster-manager/internal/models"
	"context"
	"fmt"

	"github.com/spf13/viper"
	"gorm.io/gorm"
)

type Infra struct {
	db *gorm.DB
	mq mq.MQ
}

var instance *Infra

func GetDB() *gorm.DB {
	return instance.db
}

func GetMQ() mq.MQ {
	return instance.mq
}

func InitInfra() error {

	// Init Corresponding Component according to config

	// === Init Logger ===

	if err := logger.InitLogger(); err != nil {
		return fmt.Errorf("logger init failed: %w", err)
	}

	// === Init DB ===
	dsn := fmt.Sprintf(
		"%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		viper.GetString("db.mysql.user"),
		viper.GetString("db.mysql.password"),
		viper.GetString("db.mysql.host"),
		viper.GetInt("db.mysql.port"),
		viper.GetString("db.mysql.dbname"),
	)

	db, err := db.InitDB(dsn)
	if err != nil {
		return fmt.Errorf("mysql init failed: %w", err)
	}

	if err := models.RegisterModels(db); err != nil {
		return fmt.Errorf("model migration failed: %w", err)
	}

	// === Init MQ ===

	mqConfig, err := ReadMQConfigFromViper()
	if err != nil {
		return fmt.Errorf("mq config read failed: %w", err)
	}
	mqImpl, err := mq.InitMQ(context.Background(), mqConfig)
	if err != nil {
		return fmt.Errorf("mq init failed: %w", err)
	}

	// === Bind Global Infra ===
	instance = &Infra{
		db: db,
		mq: mqImpl,
	}
	return nil
}

func ReadMQConfigFromViper() (mq.MQConfig, error) {
	mqType := viper.GetString("mq.type")
	switch mqType {
	case "redis":
		redisConfig := &mq.RedisConfig{
			Addr:       viper.GetString("mq.redis.addr"),
			Password:   viper.GetString("mq.redis.password"),
			DB:         viper.GetInt("mq.redis.db"),
			Stream:     viper.GetString("mq.redis.stream"),
			Group:      viper.GetString("mq.redis.group"),
			ConsumerID: viper.GetString("mq.redis.consumer_id"),
		}
		return mq.MQConfig{
			Type:  mq.MQRedis,
			Redis: redisConfig,
		}, nil
	case "kafka":
		return mq.MQConfig{
			Type: mq.MQKafka,
		}, fmt.Errorf("kafka config not implemented")
	}
	return mq.MQConfig{}, fmt.Errorf("unsupported mq type: %s", mqType)
}
