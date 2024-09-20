module chaincode-go-bpmn

go 1.14

require (
	IBC/Oracle v0.0.0
	github.com/hyperledger/fabric-chaincode-go v0.0.0-20210718160520-38d29fabecb9
	github.com/hyperledger/fabric-contract-api-go v1.1.1
	github.com/hyperledger/fabric-protos-go v0.0.0-20201028172056-a3136dde2354
	github.com/stretchr/testify v1.5.1
	google.golang.org/protobuf v1.26.0
)

replace IBC/Oracle => ../../../oracle-go
