package main

import (
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/smartcontractkit/libocr/offchainreporting/confighelper"
	"github.com/smartcontractkit/libocr/offchainreporting/types"
	"golang.org/x/crypto/curve25519"
	"golang.org/x/crypto/ed25519"
)

type NodeInfo struct {
	Name                 string `json:"name"`
	EthAddress           string `json:"ethAddress"`
	SignerAddress        string `json:"signerAddress"`
	OCROffchainPublicKey string `json:"ocrOffchainPublicKey"`
	OCRConfigPublicKey   string `json:"ocrConfigPublicKey"`
	P2PPeerID            string `json:"p2pPeerId"`
}

type ConfigParams struct {
	DeltaProgressSeconds int   `json:"deltaProgressSeconds"`
	DeltaResendSeconds   int   `json:"deltaResendSeconds"`
	DeltaRoundSeconds    int   `json:"deltaRoundSeconds"`
	DeltaGraceSeconds    int   `json:"deltaGraceSeconds"`
	DeltaCSeconds        int   `json:"deltaCSeconds"`
	AlphaPPB             uint64`json:"alphaPPB"`
	DeltaStageSeconds    int   `json:"deltaStageSeconds"`
	RMax                 uint8 `json:"rMax"`
	S                    []int `json:"s"`
}

type OracleInfo struct {
	Name                 string `json:"name"`
	SignerAddress        string `json:"signerAddress"`
	TransmitterAddress   string `json:"transmitterAddress"`
	P2PPeerID            string `json:"p2pPeerId"`
	OCROffchainPublicKey string `json:"ocrOffchainPublicKey"`
	OCRConfigPublicKey   string `json:"ocrConfigPublicKey"`
}

type GeneratedConfig struct {
	GeneratedAt         string       `json:"generatedAt"`
	Signers             []string     `json:"signers"`
	Transmitters        []string     `json:"transmitters"`
	Threshold           int          `json:"threshold"`
	EncodedConfigVersion uint64      `json:"encodedConfigVersion"`
	EncodedConfigHex    string       `json:"encodedConfigHex"`
	Params              ConfigParams `json:"params"`
	Oracles             []OracleInfo `json:"oracles"`
}

func normalizeKey(raw string) string {
	value := strings.TrimSpace(raw)
	if value == "" {
		return ""
	}
	if idx := strings.LastIndex(value, "_"); idx != -1 {
		value = value[idx+1:]
	}
	value = strings.TrimPrefix(value, "0x")
	return strings.ToLower(value)
}

func decodeHexBytes(raw string, expectedLen int) ([]byte, error) {
	normalized := normalizeKey(raw)
	if normalized == "" {
		return nil, errors.New("empty key")
	}
	if len(normalized)%2 == 1 {
		normalized = "0" + normalized
	}
	decoded, err := hex.DecodeString(normalized)
	if err != nil {
		return nil, err
	}
	if expectedLen > 0 && len(decoded) != expectedLen {
		return nil, fmt.Errorf("unexpected key length: got %d want %d", len(decoded), expectedLen)
	}
	return decoded, nil
}

func parseSignerAddress(raw string) (common.Address, error) {
	normalized := normalizeKey(raw)
	if normalized == "" {
		return common.Address{}, errors.New("empty signer address")
	}
	if len(normalized) != 40 {
		return common.Address{}, fmt.Errorf("unexpected signer address length: %d", len(normalized))
	}
	return common.HexToAddress("0x" + normalized), nil
}

func parseOffchainPublicKey(raw string) (types.OffchainPublicKey, error) {
	decoded, err := decodeHexBytes(raw, ed25519.PublicKeySize)
	if err != nil {
		return nil, err
	}
	return types.OffchainPublicKey(decoded), nil
}

func parseConfigPublicKey(raw string) (types.SharedSecretEncryptionPublicKey, error) {
	decoded, err := decodeHexBytes(raw, curve25519.PointSize)
	if err != nil {
		return types.SharedSecretEncryptionPublicKey{}, err
	}
	var key types.SharedSecretEncryptionPublicKey
	copy(key[:], decoded)
	return key, nil
}

func main() {
	nodeInfoPath := filepath.FromSlash("deployment/node-info.json")
	outputPath := filepath.FromSlash("deployment/ocr-config-gen.json")
	if _, err := os.Stat(nodeInfoPath); err != nil {
		altPaths := []string{
			filepath.FromSlash("../deployment/node-info.json"),
			filepath.FromSlash("../../deployment/node-info.json"),
		}
		found := false
		for _, altPath := range altPaths {
			if _, altErr := os.Stat(altPath); altErr == nil {
				nodeInfoPath = altPath
				outputPath = filepath.FromSlash(filepath.Dir(altPath) + "/ocr-config-gen.json")
				found = true
				break
			}
		}
		if !found {
			// keep default paths to preserve error messages below
		}
	}

	data, err := os.ReadFile(nodeInfoPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to read %s: %v\n", nodeInfoPath, err)
		os.Exit(1)
	}

	var nodes []NodeInfo
	if err := json.Unmarshal(data, &nodes); err != nil {
		fmt.Fprintf(os.Stderr, "failed to parse %s: %v\n", nodeInfoPath, err)
		os.Exit(1)
	}

	oracles := make([]NodeInfo, 0, len(nodes))
	for _, node := range nodes {
		if strings.EqualFold(node.Name, "bootstrap") {
			continue
		}
		oracles = append(oracles, node)
	}

	if len(oracles) < 4 {
		fmt.Fprintf(os.Stderr, "need at least 4 oracle nodes (excluding bootstrap), got %d\n", len(oracles))
		os.Exit(1)
	}

	s := make([]int, len(oracles))
	for i := range s {
		s[i] = 1
	}

	deltaProgress := 30 * time.Second
	deltaResend := 30 * time.Second
	deltaRound := 20 * time.Second
	deltaGrace := 10 * time.Second
	deltaC := 10 * time.Minute
	alphaPPB := uint64(1)
	deltaStage := 10 * time.Second
	rMax := uint8(3)
	f := (len(oracles) - 1) / 3

	oracleIdentities := make([]confighelper.OracleIdentityExtra, 0, len(oracles))
	oracleInfos := make([]OracleInfo, 0, len(oracles))

	for _, node := range oracles {
		if node.SignerAddress == "" || node.EthAddress == "" || node.OCROffchainPublicKey == "" || node.OCRConfigPublicKey == "" || node.P2PPeerID == "" {
			fmt.Fprintf(os.Stderr, "missing required OCR fields for node %s\n", node.Name)
			os.Exit(1)
		}

		signerAddr, err := parseSignerAddress(node.SignerAddress)
		if err != nil {
			fmt.Fprintf(os.Stderr, "invalid signer address for node %s: %v\n", node.Name, err)
			os.Exit(1)
		}
		transmitterAddr := common.HexToAddress("0x" + normalizeKey(node.EthAddress))

		offchainPK, err := parseOffchainPublicKey(node.OCROffchainPublicKey)
		if err != nil {
			fmt.Fprintf(os.Stderr, "invalid offchain public key for node %s: %v\n", node.Name, err)
			os.Exit(1)
		}
		configPK, err := parseConfigPublicKey(node.OCRConfigPublicKey)
		if err != nil {
			fmt.Fprintf(os.Stderr, "invalid config public key for node %s: %v\n", node.Name, err)
			os.Exit(1)
		}

		oracleIdentities = append(oracleIdentities, confighelper.OracleIdentityExtra{
			OracleIdentity: confighelper.OracleIdentity{
				OnChainSigningAddress: types.OnChainSigningAddress(signerAddr),
				TransmitAddress:       transmitterAddr,
				OffchainPublicKey:     offchainPK,
				PeerID:                node.P2PPeerID,
			},
			SharedSecretEncryptionPublicKey: configPK,
		})

		oracleInfos = append(oracleInfos, OracleInfo{
			Name:                 node.Name,
			SignerAddress:        signerAddr.Hex(),
			TransmitterAddress:   transmitterAddr.Hex(),
			P2PPeerID:            node.P2PPeerID,
			OCROffchainPublicKey: node.OCROffchainPublicKey,
			OCRConfigPublicKey:   node.OCRConfigPublicKey,
		})
	}

	signers, transmitters, threshold, encodedConfigVersion, encodedConfig, err := confighelper.ContractSetConfigArgs(
		deltaProgress,
		deltaResend,
		deltaRound,
		deltaGrace,
		deltaC,
		alphaPPB,
		deltaStage,
		rMax,
		s,
		oracleIdentities,
		f,
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to generate config: %v\n", err)
		os.Exit(1)
	}

	signersHex := make([]string, 0, len(signers))
	for _, signer := range signers {
		signersHex = append(signersHex, signer.Hex())
	}

	transmittersHex := make([]string, 0, len(transmitters))
	for _, transmitter := range transmitters {
		transmittersHex = append(transmittersHex, transmitter.Hex())
	}

	generated := GeneratedConfig{
		GeneratedAt:          time.Now().UTC().Format(time.RFC3339),
		Signers:              signersHex,
		Transmitters:         transmittersHex,
		Threshold:            int(threshold),
		EncodedConfigVersion: encodedConfigVersion,
		EncodedConfigHex:     "0x" + hex.EncodeToString(encodedConfig),
		Params: ConfigParams{
			DeltaProgressSeconds: int(deltaProgress.Seconds()),
			DeltaResendSeconds:   int(deltaResend.Seconds()),
			DeltaRoundSeconds:    int(deltaRound.Seconds()),
			DeltaGraceSeconds:    int(deltaGrace.Seconds()),
			DeltaCSeconds:        int(deltaC.Seconds()),
			AlphaPPB:             alphaPPB,
			DeltaStageSeconds:    int(deltaStage.Seconds()),
			RMax:                 rMax,
			S:                    s,
		},
		Oracles: oracleInfos,
	}

	outputBytes, err := json.MarshalIndent(generated, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to encode output: %v\n", err)
		os.Exit(1)
	}

	if err := os.WriteFile(outputPath, outputBytes, 0o644); err != nil {
		fmt.Fprintf(os.Stderr, "failed to write %s: %v\n", outputPath, err)
		os.Exit(1)
	}

	fmt.Printf("generated OCR config: %s\n", outputPath)
}
