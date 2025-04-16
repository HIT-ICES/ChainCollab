package provider

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"cluster-manager/internal/models"

	"github.com/docker/docker/api/types/container"
	"github.com/docker/docker/api/types/filters"
	"github.com/docker/docker/api/types/image"
	"github.com/docker/docker/api/types/network"
	"github.com/docker/docker/client"
	"github.com/docker/docker/pkg/jsonmessage"
)

type DockerProvider struct {
	providerID string
	host       string
	cli        *client.Client
}

func parseTime(created string) time.Time {
	parsedTime, err := time.Parse(time.RFC3339, created)
	if err != nil {
		return time.Time{} // Return zero value if parsing fails
	}
	return parsedTime
}

func NewDockerProvider(p models.Provider) (*DockerProvider, error) {
	cli, err := client.NewClientWithOpts(
		client.FromEnv,
		client.WithAPIVersionNegotiation(),
	)
	if err != nil {
		return nil, err
	}
	// test cli
	// 测试连接是否可用
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_, err = cli.Ping(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to ping Docker daemon at %s:%d: %w", p.Host, p.Port, err)
	}

	return &DockerProvider{
		providerID: p.ID,
		host:       p.Host,
		cli:        cli,
	}, nil
}

func (d *DockerProvider) ID() string   { return d.providerID }
func (d *DockerProvider) Type() string { return "docker" }

// pullImageIfNotExists 检查镜像是否存在，如果不存在，则拉取镜像
func (d *DockerProvider) pullImageIfNotExists(imageName string) error {
	ctx := context.Background()

	// 检查镜像是否存在
	_, err := d.cli.ImageInspect(ctx, imageName)
	if client.IsErrNotFound(err) {
		// 镜像不存在，进行拉取
		fmt.Println("Image not found, pulling image:", imageName)
		out, err := d.cli.ImagePull(ctx, imageName, image.PullOptions{All: false})
		if err != nil {
			return fmt.Errorf("failed to pull image: %v", err)
		}
		defer out.Close()

		// 打印拉取过程
		decoder := json.NewDecoder(out)
		for {
			var msg jsonmessage.JSONMessage
			if err := decoder.Decode(&msg); err != nil {
				break
			}
			fmt.Println(msg)
		}
	} else if err != nil {
		// 如果发生其他错误
		return fmt.Errorf("failed to inspect image: %v", err)
	}

	return nil
}

func (d *DockerProvider) DeployProgram(spec ProgramSpec) (ProgramStatus, error) {
	ctx := context.Background()

	// 确保镜像存在，如果不存在则拉取
	if err := d.pullImageIfNotExists(spec.Command); err != nil {
		return ProgramStatus{}, err
	}

	// 创建容器配置
	config := &container.Config{
		Image:  spec.Command, // 镜像名
		Env:    flattenEnv(spec.Env),
		Cmd:    spec.Args,
		Labels: spec.Labels,
	}

	hostCfg := &container.HostConfig{}
	if len(spec.Volumes) > 0 {
		binds := []string{}
		for hostPath, containerPath := range spec.Volumes {
			binds = append(binds, fmt.Sprintf("%s:%s", hostPath, containerPath))
		}
		hostCfg.Binds = binds
	}

	networkCfg := &network.NetworkingConfig{}
	if spec.Network != "" {
		// 如果需要特定的网络，可以配置
	}

	containerName := spec.Name

	// 创建容器
	resp, err := d.cli.ContainerCreate(ctx, config, hostCfg, networkCfg, nil, containerName)
	if err != nil {
		return ProgramStatus{}, err
	}

	// 启动容器
	err = d.cli.ContainerStart(ctx, resp.ID, container.StartOptions{})
	if err != nil {
		return ProgramStatus{}, err
	}

	return ProgramStatus{
		ID:      resp.ID,
		Name:    containerName,
		Status:  "running",
		Message: "Container started",
		Created: time.Now(),
	}, nil
}

func (d *DockerProvider) StopProgram(programID string) error {
	ctx := context.Background()
	timeout := 5 * time.Second
	timeoutSeconds := int(timeout.Seconds())
	return d.cli.ContainerStop(ctx, programID, container.StopOptions{Timeout: &timeoutSeconds})
}

func (d *DockerProvider) UpdateProgram(spec ProgramSpec) (ProgramStatus, error) {
	// 简化处理：先停止再重建（更优方式是 diff config 后动态更新）
	err := d.StopProgram(spec.ID)
	if err != nil {
		return ProgramStatus{}, err
	}
	return d.DeployProgram(spec)
}

func (d *DockerProvider) GetStatus(programID string) (ProgramStatus, error) {
	ctx := context.Background()
	info, err := d.cli.ContainerInspect(ctx, programID)
	if err != nil {
		return ProgramStatus{}, err
	}

	status := "unknown"
	if info.State.Running {
		status = "running"
	} else if info.State.Status == "exited" {
		status = "stopped"
	} else if info.State.Status != "" {
		status = info.State.Status
	}

	return ProgramStatus{
		ID:      programID,
		Name:    info.Name,
		Status:  status,
		Message: info.State.Status,
		Created: parseTime(info.Created),
	}, nil
}

func (d *DockerProvider) ListProgramsByLabel(key, value string) ([]ProgramStatus, error) {
	ctx := context.Background()
	args := filters.NewArgs()
	args.Add("label", fmt.Sprintf("%s=%s", key, value))

	containers, err := d.cli.ContainerList(ctx, container.ListOptions{
		All:     true,
		Filters: args,
	})
	if err != nil {
		return nil, err
	}

	var statuses []ProgramStatus
	for _, c := range containers {
		status := "unknown"
		if c.State == "running" {
			status = "running"
		} else if c.State != "" {
			status = c.State
		}

		created := time.Unix(c.Created, 0)
		statuses = append(statuses, ProgramStatus{
			ID:      c.ID,
			Name:    c.Names[0],
			Status:  status,
			Message: c.Status,
			Created: created,
		})
	}

	return statuses, nil
}

// 无需实现 Provider 中的 GetProvider，这更像是工厂函数，移出接口
func (d *DockerProvider) GetProvider(p models.Provider) (*Provider, error) {
	return nil, fmt.Errorf("deprecated: use NewDockerProvider() instead")
}

func flattenEnv(env map[string]string) []string {
	result := []string{}
	for k, v := range env {
		result = append(result, fmt.Sprintf("%s=%s", k, v))
	}
	return result
}

func (d *DockerProvider) GetClusterStatus(clusterID string) (map[string]ProgramStatus, error) {
	ctx := context.Background()
	args := filters.NewArgs()
	args.Add("label", fmt.Sprintf("cluster_id=%s", clusterID))

	containers, err := d.cli.ContainerList(ctx, container.ListOptions{
		All:     true,
		Filters: args,
	})
	if err != nil {
		return nil, err
	}

	statuses := make(map[string]ProgramStatus)
	for _, c := range containers {
		status := "unknown"
		if c.State == "running" {
			status = "running"
		} else if c.State != "" {
			status = c.State
		}

		created := time.Unix(c.Created, 0)
		statuses[c.ID] = ProgramStatus{
			ID:      c.ID,
			Name:    c.Names[0],
			Status:  status,
			Message: c.Status,
			Created: created,
		}
	}

	return statuses, nil
}
