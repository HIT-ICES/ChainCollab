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
	K           int              `json:"k"`
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

	places := map[string]Place{
		"P_INIT":   {ID: "P_INIT", Tokens: []Token{}},
		"P_DONE_I": {ID: "P_DONE_I", Tokens: []Token{}},
		"P_DONE":   {ID: "P_DONE", Tokens: []Token{}},
	}
	transitions := []Transition{}

	// P_INIT 初始 Token 是 IDList（颜色为 P0, P1, ..., Pn）
	for i := 0; i < nInt; i++ {
		color := fmt.Sprintf("P%d", i)
		pInit := places["P_INIT"]
		pInit.Tokens = append(pInit.Tokens, Token{Color: color})
		places["P_INIT"] = pInit

		// 每个 P{i} 初始化为空
		places[color] = Place{ID: color, Tokens: []Token{}}

		// T_INIT 拆解 IDList -> P{i}
		transitions = append(transitions, Transition{
			ID: fmt.Sprintf("T_INIT_%d", i),
			InputArcs: []Arc{
				{PlaceID: "P_INIT", Color: color},
			},
			OutputArcs: []Arc{
				{PlaceID: color, Color: color},
			},
			Activated: false,
		})

		// T_i: P{i} -> P_DONE_I
		transitions = append(transitions, Transition{
			ID: fmt.Sprintf("T_%d", i),
			InputArcs: []Arc{
				{PlaceID: color, Color: color},
			},
			OutputArcs: []Arc{
				{PlaceID: "P_DONE_I", Color: color},
			},
			Activated: false,
		})

		// 从 P_INIT 中移除 token
		pInit.Tokens = removeTokenByColor(pInit.Tokens, color)
		places["P_INIT"] = pInit

		// 放入对应的 P{i}
		pi := places[color]
		pi.Tokens = append(pi.Tokens, Token{Color: color})
		places[color] = pi

		// 标记 T_INIT_i 为已激活
		tid := fmt.Sprintf("T_INIT_%d", i)
		for j := range transitions {
			if transitions[j].ID == tid {
				transitions[j].Activated = true
				break
			}
		}
	}

	// T_COMPLETE：length(P_DONE_I.tokens) >= K -> P_DONE
	transitions = append(transitions, Transition{
		ID: "T_COMPLETE",
		InputArcs: []Arc{
			{PlaceID: "P_DONE_I", Color: "*"}, // 使用 "*" 作为 wildcard
		},
		OutputArcs: []Arc{
			{PlaceID: "P_DONE", Color: "COMPLETE"},
		},
		Activated: false,
	})

	state := CPNState{
		Places:      places,
		Transitions: transitions,
		K:           kInt,
	}
	data, _ := json.Marshal(state)
	return ctx.GetStub().PutState("cpnState", data)
}

// ========== 参与方调用完成 ==========
func (s *SmartContract) MarkDone(ctx contractapi.TransactionContextInterface, participantID string) error {
	state, err := getCPNState(ctx)
	if err != nil {
		return err
	}

	// 扫描所有 Transition，寻找可激发的（包含该参与方）
	for ti, t := range state.Transitions {
		if t.Activated {
			continue
		}

		// T_i 类型 transition: 输入是 P{participantID}，颜色也是 participantID
		if len(t.InputArcs) == 1 &&
			t.InputArcs[0].PlaceID == participantID &&
			t.InputArcs[0].Color == participantID {

			// 检查是否存在匹配 token
			p := state.Places[participantID]
			found := false
			for _, tok := range p.Tokens {
				if tok.Color == participantID {
					found = true
					break
				}
			}
			if !found {
				continue
			}

			// 激发 Transition
			p.Tokens = removeTokenByColor(p.Tokens, participantID)
			state.Places[participantID] = p

			outP := state.Places["P_DONE_I"]
			outP.Tokens = append(outP.Tokens, Token{Color: participantID})
			state.Places["P_DONE_I"] = outP

			state.Transitions[ti].Activated = true
		}
	}

	// 检查是否可激发 T_COMPLETE
	for ti, t := range state.Transitions {
		if t.ID != "T_COMPLETE" || t.Activated {
			continue
		}
		donePlace := state.Places["P_DONE_I"]
		if len(donePlace.Tokens) >= state.K {
			// 激发 T_COMPLETE
			pDone := state.Places["P_DONE"]
			pDone.Tokens = append(pDone.Tokens, Token{Color: "COMPLETE"})
			state.Places["P_DONE"] = pDone
			state.Transitions[ti].Activated = true
		}
	}

	newData, _ := json.Marshal(state)
	return ctx.GetStub().PutState("cpnState", newData)
}

// ========== 查询状态 ==========
type QueryResult struct {
	State CPNState `json:"state"`
	PDone bool     `json:"p_done"`
}

func (s *SmartContract) QueryStatus(ctx contractapi.TransactionContextInterface) (*QueryResult, error) {
	state, err := getCPNState(ctx)
	if err != nil {
		return nil, err
	}

	done := false
	if p, ok := state.Places["P_DONE"]; ok {
		for _, token := range p.Tokens {
			if token.Color == "COMPLETE" {
				done = true
			}
		}
	}
	return &QueryResult{State: state, PDone: done}, nil
}

// ========== 工具函数 ==========
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

func removeTokenByColor(tokens []Token, color string) []Token {
	result := []Token{}
	removed := false
	for _, t := range tokens {
		if t.Color == color && !removed {
			removed = true
			continue
		}
		result = append(result, t)
	}
	return result
}

func main() {
	cc, err := contractapi.NewChaincode(new(SmartContract))
	if err != nil {
		panic(err)
	}
	if err := cc.Start(); err != nil {
		panic(err)
	}
}
