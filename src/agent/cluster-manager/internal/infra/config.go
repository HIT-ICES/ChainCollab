package infra

import (
	"log"

	"github.com/spf13/viper"
)

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
