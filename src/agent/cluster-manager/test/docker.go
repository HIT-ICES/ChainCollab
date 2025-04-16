package main

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/docker/docker/client"
)

func main() {
	cli, err := client.NewClientWithOpts(
		client.WithHost("http://localhost:2375"),
		client.WithHTTPClient(&http.Client{}), // Force HTTP
		client.WithAPIVersionNegotiation(),
	)
	if err != nil {
		fmt.Println("error: could not create docker client handle")
		fmt.Println(err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	res, err := cli.Ping(ctx)
	if err != nil {
		fmt.Println(res)
		fmt.Println("failed to ping Docker daemon")
	}
}
