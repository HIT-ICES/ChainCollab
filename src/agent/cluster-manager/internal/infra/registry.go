package infra

import (
	"cluster-manager/internal/models"
	"fmt"

	"github.com/spf13/viper"
)

func InitInfra(configPath string) error {
	if err := InitConfig(configPath); err != nil {
		return fmt.Errorf("config init failed: %w", err)
	}

	if err := InitLogger(); err != nil {
		return fmt.Errorf("logger init failed: %w", err)
	}

	dsn := fmt.Sprintf(
		"%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		viper.GetString("database.mysql.user"),     // "root"
		viper.GetString("database.mysql.password"), // "password"
		viper.GetString("database.mysql.host"),     // "localhost"（需改为 "mysql" 如果跑在 Docker）
		viper.GetInt("database.mysql.port"),        // 3306
		viper.GetString("database.mysql.dbname"),   // "devdb"
	)

	if err := InitMySQL(dsn); err != nil {
		return fmt.Errorf("mysql init failed: %w", err)
	}

	// Migrate all models
	if err := models.RegisterModels(DB); err != nil {
		return fmt.Errorf("model migration failed: %w", err)
	}

	if err := InitRedis(
		viper.GetString("redis.addr"),
		viper.GetString("redis.password"),
		viper.GetInt("redis.db"),
	); err != nil {
		return fmt.Errorf("redis init failed: %w", err)
	}

	return nil
}
