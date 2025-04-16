package utils

import (
	"math/rand"
	"time"

	"github.com/google/uuid"
)

// 生成短随机ID
func RandomShortID() string {
	// 使用时间戳创建一个新的随机源
	src := rand.NewSource(time.Now().UnixNano())
	rand.New(src)

	// 生成一个新的UUID，并取其前8个字符
	return uuid.New().String()[:8]
}
