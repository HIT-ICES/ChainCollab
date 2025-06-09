#!/bin/bash
export PATH=~/code/fabric-samples/bin:$PATH
export FABRIC_CFG_PATH=~/code/fabric-samples/config
export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_LOCALMSPID="Org1MSP"
export CORE_PEER_TLS_ROOTCERT_FILE=~/code/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
export CORE_PEER_MSPCONFIGPATH=~/code/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
export CORE_PEER_ADDRESS=localhost:7051

ORDERER_CA=~/code/fabric-samples/test-network/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
CHAINCODE_NAME=basic
CHANNEL=mychannel
PEER0_ORG1_CA=$CORE_PEER_TLS_ROOTCERT_FILE
PEER0_ORG2_CA=~/code/fabric-samples/test-network/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt

for N in $(seq 5 50 305); do
  # K=$((N / 2))
  K=3 # 固定 K 为 3
  PARTICIPANTS="["
  for ((i = 0; i < N; i++)); do
    PARTICIPANTS+="\"P$i\""
    if [ $i -lt $((N - 1)) ]; then
      PARTICIPANTS+=","
    fi
  done
  PARTICIPANTS+="]"
  # echo "Participants: $PARTICIPANTS"

  echo "Testing N=$N, K=$K"

  INIT_ARGS=$(jq -c -n --arg p "$PARTICIPANTS" --arg k "$K" '{"function":"InitProcess","Args":[ $p, $k ]}')
  peer chaincode invoke -o localhost:7050 \
    --ordererTLSHostnameOverride orderer.example.com \
    --tls --cafile "$ORDERER_CA" \
    -C $CHANNEL -n $CHAINCODE_NAME \
    --peerAddresses localhost:7051 \
    --tlsRootCertFiles "$PEER0_ORG1_CA" \
    --peerAddresses localhost:9051 \
    --tlsRootCertFiles "$PEER0_ORG2_CA" \
    -c "$INIT_ARGS"

  sleep 3 # 给链码时间初始化

  echo "Starting time: $start_time"
  total_invoke_duration=0

  if [ $N -le 200 ]; then
    sleep_time=2
  else
    sleep_time=$((2 + (N) /100))
  fi

  for ((j = 0; j < K; j++)); do
    echo "Invoking MarkDone for P$j"
    invoke_start=$(date +%s%3N)
    peer chaincode invoke -o localhost:7050 \
      --ordererTLSHostnameOverride orderer.example.com \
      --tls --cafile "$ORDERER_CA" \
      -C $CHANNEL -n $CHAINCODE_NAME \
      --peerAddresses localhost:7051 \
      --tlsRootCertFiles "$PEER0_ORG1_CA" \
      --peerAddresses localhost:9051 \
      --tlsRootCertFiles "$PEER0_ORG2_CA" \
      -c "{\"function\":\"MarkDone\",\"Args\":[\"P$j\"]}"
    invoke_end=$(date +%s%3N)
    invoke_duration=$((invoke_end - invoke_start))
    total_invoke_duration=$((total_invoke_duration + invoke_duration))
    echo "Invoke $j duration: ${invoke_duration}ms"
    sleep $sleep_time
    QUERY_RESULT=$(peer chaincode query -C $CHANNEL -n $CHAINCODE_NAME -c '{"function":"QueryStatus","Args":[]}')
    echo "Query result after invoke $j: $QUERY_RESULT"
  done

  sleep 4 # 等待所有 invoke 完成
  # 查询链码状态
  QUERY_RESULT=$(peer chaincode query -C $CHANNEL -n $CHAINCODE_NAME -c '{"function":"QueryStatus","Args":[]}')
  echo "Query result: $QUERY_RESULT"
  # 提取 p_done 字段
  P_DONE=$(echo "$QUERY_RESULT" | jq -r '.p_done')

  echo "N=$N, K=$K, TotalTime=${total_invoke_duration}ms, P_DONE=$P_DONE"

  if [ "$P_DONE" != "true" ]; then
    echo "❌ P_DONE is not true! Test failed for N=$N, K=$K"
    exit 1
  fi

  echo "✅ P_DONE is true! Test passed for N=$N, K=$K"
done
