package chaincode

import (
	"encoding/json"
	"fmt"
	"strconv"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type Token struct {
	Color string `json:"color"` // 参与方 ID
}

type Place struct {
	ID     string  `json:"id"`
	Tokens []Token `json:"tokens"`
}

type Arc struct {
	PlaceID string `json:"place_id"` // 输入/输出位置
	Color   string `json:"color"`    // 所需 token 颜色
}

type Transition struct {
	ID         string `json:"id"`
	InputArcs  []Arc  `json:"input_arcs"`
	OutputArcs []Arc  `json:"output_arcs"`
	Activated  bool   `json:"activated"`
}

type CPNState struct {
	Places      map[string]Place `json:"places"`
	Transitions []Transition     `json:"transitions"`
}

// ============================
// 初始化函数（参与方数量、K值、起始点）
// ============================
func (s *SmartContract) InitProcess(ctx contractapi.TransactionContextInterface, n string, k string) error {
	nInt, err := strconv.Atoi(n)
	if err != nil {
		return fmt.Errorf("invalid n input: %v", err)
	}
	kInt, err := strconv.Atoi(k)
	if err != nil {
		return fmt.Errorf("invalid k input: %v", err)
	}

	// 构造参与方 ID：P0, P1, ..., P(n-1)
	participants := make([]string, nInt)
	for i := 0; i < nInt; i++ {
		participants[i] = fmt.Sprintf("P%d", i)
	}

	// 初始化 place
	places := make(map[string]Place)
	for _, p := range participants {
		places[p] = Place{ID: p, Tokens: []Token{}}
	}
	places["P_DONE"] = Place{ID: "P_DONE", Tokens: []Token{}} // 最终输出 place

	// 构造 Transition，只使用前 k 个作为示例
	inputArcs := []Arc{}
	for i := 0; i < kInt && i < nInt; i++ {
		inputArcs = append(inputArcs, Arc{
			PlaceID: participants[i],
			Color:   participants[i],
		})
	}

	outputArcs := []Arc{
		{PlaceID: "P_DONE", Color: "COMPLETE"},
	}

	transitions := []Transition{
		{
			ID:         "T_COMPLETE",
			InputArcs:  inputArcs,
			OutputArcs: outputArcs,
			Activated:  false,
		},
	}

	state := CPNState{
		Places:      places,
		Transitions: transitions,
	}
	data, _ := json.Marshal(state)
	return ctx.GetStub().PutState("cpnState", data)
}

// ============================
// MarkDone（添加 colored token）
// ============================
func (s *SmartContract) MarkDone(ctx contractapi.TransactionContextInterface, participantID string) error {
	state, err := getCPNState(ctx)
	if err != nil {
		return err
	}

	place, ok := state.Places[participantID]
	if !ok {
		return fmt.Errorf("actor place not found")
	}

	// 添加 token
	for _, token := range place.Tokens {
		if token.Color == participantID {
			return nil // 忽略重复
		}
	}
	place.Tokens = append(place.Tokens, Token{Color: participantID})
	state.Places[participantID] = place

	// 检查是否可激发 transition
	for ti, t := range state.Transitions {
		if t.Activated {
			continue
		}
		canFire := true
		for _, arc := range t.InputArcs {
			p, ok := state.Places[arc.PlaceID]
			if !ok {
				canFire = false
				break
			}
			found := false
			for _, token := range p.Tokens {
				if token.Color == arc.Color {
					found = true
					break
				}
			}
			if !found {
				canFire = false
				break
			}
		}
		if canFire {
			// Fire transition
			for _, arc := range t.InputArcs {
				p := state.Places[arc.PlaceID]
				newTokens := []Token{}
				for _, token := range p.Tokens {
					if token.Color != arc.Color {
						newTokens = append(newTokens, token)
					}
				}
				p.Tokens = newTokens
				state.Places[arc.PlaceID] = p
			}
			for _, arc := range t.OutputArcs {
				p := state.Places[arc.PlaceID]
				p.Tokens = append(p.Tokens, Token{Color: arc.Color})
				state.Places[arc.PlaceID] = p
			}
			state.Transitions[ti].Activated = true
		}
	}

	newData, _ := json.Marshal(state)
	return ctx.GetStub().PutState("cpnState", newData)
}

// ============================
// 查询状态
// ============================
type QueryResult struct {
	State CPNState `json:"state"`
	PDone bool     `json:"p_done"`
}

func (s *SmartContract) QueryStatus(ctx contractapi.TransactionContextInterface) (*QueryResult, error) {
	state, err := getCPNState(ctx)
	if err != nil {
		return nil, err
	}

	// 检查 P_DONE 中是否存在颜色为 "COMPLETE" 的 token
	pDone := false
	if place, exists := state.Places["P_DONE"]; exists {
		for _, token := range place.Tokens {
			if token.Color == "COMPLETE" {
				pDone = true
				break
			}
		}
	}

	result := &QueryResult{
		State: state,
		PDone: pDone,
	}
	return result, nil
}

// ============================
// 工具函数：读写状态
// ============================
func getCPNState(ctx contractapi.TransactionContextInterface) (CPNState, error) {
	var state CPNState
	data, err := ctx.GetStub().GetState("cpnState")
	if err != nil || data == nil {
		return state, fmt.Errorf("state not found or error")
	}
	if err := json.Unmarshal(data, &state); err != nil {
		return state, err
	}
	return state, nil
}

func main() {
	chaincode, err := contractapi.NewChaincode(new(SmartContract))
	if err != nil {
		panic(fmt.Sprintf("Error creating chaincode: %v", err))
	}
	if err := chaincode.Start(); err != nil {
		panic(fmt.Sprintf("Error starting chaincode: %v", err))
	}
}
