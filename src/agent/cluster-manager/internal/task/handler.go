package task

import (
	"cluster-manager/internal/infra"
	"cluster-manager/internal/models"
	"cluster-manager/internal/provider"
	"cluster-manager/internal/repository"
	"encoding/json"
	"fmt"
)

func InitTaskHandler() {
	initIPFS()
}

type ExecHandlerFunc func(raw json.RawMessage, prov provider.Provider) (any, error)
type InputAssertionFunc func(raw json.RawMessage) (interface{}, error)

type TaskExecutor struct {
	Handler ExecHandlerFunc
	Assert  InputAssertionFunc // 可选
}

var execHandlers = make(map[string]TaskExecutor)

func RegisterExecHandler(taskType, action string, handler ExecHandlerFunc, assert InputAssertionFunc) {
	key := fmt.Sprintf("%s:%s", taskType, action)
	execHandlers[key] = TaskExecutor{Handler: handler, Assert: assert}
}

func executeTask(taskRecord *models.Task, prov provider.Provider) (any, error) {
	key := fmt.Sprintf("%s:%s", taskRecord.Type, taskRecord.Action)
	exec, ok := execHandlers[key]
	if !ok {
		return nil, fmt.Errorf("no executor found for task type %s and action %s", taskRecord.Type, taskRecord.Action)
	}
	return exec.Handler(taskRecord.Config, prov)
}

type TypeAssertionFunc func(result any) (interface{}, error)

type PostHandler func(taskRecord *models.Task, result any, prov provider.Provider) error

type PostHandlerWithAssertion struct {
	Handler       PostHandler
	TypeAssertion TypeAssertionFunc
}

var postHandlers = make(map[string]PostHandlerWithAssertion)

func RegisterPostHandler(taskType, action string, handler PostHandler, typeAssertion TypeAssertionFunc) {
	key := fmt.Sprintf("%s:%s", taskType, action)
	postHandlers[key] = PostHandlerWithAssertion{Handler: handler, TypeAssertion: typeAssertion}
}

func executePostHandler(taskRecord *models.Task, result any, prov provider.Provider) error {
	key := fmt.Sprintf("%s:%s", taskRecord.Type, taskRecord.Action)
	if postProcessor, ok := postHandlers[key]; ok {
		typedResult, err := postProcessor.TypeAssertion(result)
		if err != nil {
			return fmt.Errorf("type assertion failed: %w", err)
		}
		return postProcessor.Handler(taskRecord, typedResult, prov)
	}
	return fmt.Errorf("no post handler found for task type %s and action %s", taskRecord.Type, taskRecord.Action)
}

func HandleTask(raw string) error {
	var t struct {
		ID string `json:"task_id"`
	}
	if err := json.Unmarshal([]byte(raw), &t); err != nil {
		return fmt.Errorf("invalid task format: %w", err)
	}

	taskManager := &repository.TaskManager{DB: infra.DB}
	taskRecord, err := taskManager.GetTaskByID(t.ID)
	if err != nil {
		return fmt.Errorf("failed to get task: %w", err)
	}

	_ = taskManager.UpdateTaskStatus(t.ID, "running", nil, "")

	providerManager := &repository.ProviderManager{DB: infra.DB}
	providerRecord, err := providerManager.GetProvider(taskRecord.ProviderID)
	if err != nil {
		_ = taskManager.UpdateTaskStatus(t.ID, "failed", nil, err.Error())
		return fmt.Errorf("get provider failed: %w", err)
	}
	prov, err := provider.InstantiateProvider(providerRecord)
	if err != nil {
		_ = taskManager.UpdateTaskStatus(t.ID, "failed", nil, err.Error())
		return fmt.Errorf("instantiate provider failed: %w", err)
	}

	result, handleErr := executeTask(taskRecord, prov)
	if handleErr != nil {
		_ = taskManager.UpdateTaskStatus(t.ID, "failed", nil, handleErr.Error())
		return handleErr
	}

	postErr := executePostHandler(taskRecord, result, prov)
	if postErr != nil {
		_ = taskManager.UpdateTaskStatus(t.ID, "failed", nil, postErr.Error())
		return postErr
	}

	_ = taskManager.UpdateTaskStatus(t.ID, "success", nil, "")
	return nil
}
