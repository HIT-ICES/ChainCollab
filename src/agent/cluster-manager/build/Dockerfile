# 使用 Go 官方镜像
FROM golang:1.19 AS builder

# 设置工作目录
WORKDIR /app

# 将当前目录中的文件复制到容器中
COPY . .

# 编译 Go 应用
RUN go build -o main .

# 使用更轻量的镜像来运行应用
FROM alpine:latest

# 安装需要的依赖
RUN apk --no-cache add ca-certificates

# 设置工作目录
WORKDIR /root/

# 从 builder 镜像中复制已编译的二进制文件
COPY --from=builder /app/main .

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["./main"]
