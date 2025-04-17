package db

import "gorm.io/gorm"

func InitDB(dsn string) (*gorm.DB, error) {
	err := InitMySQL(dsn)
	return DB, err
}
