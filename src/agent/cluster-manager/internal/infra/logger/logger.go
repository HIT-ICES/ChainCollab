package logger

import (
	"go.uber.org/zap"
)

var Logger *zap.Logger

func InitZapLogger() error {
	var err error
	Logger, err = zap.NewProduction()
	if err != nil {
		return err
	}
	zap.ReplaceGlobals(Logger)
	return nil
}
