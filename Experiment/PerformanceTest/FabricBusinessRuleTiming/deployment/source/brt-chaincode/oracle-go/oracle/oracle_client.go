package oracle

import "encoding/json"

func EncodeSetDataItemArgs(access_key string, key string, value string, data_type string) [][]byte {
	_args := make([][]byte, 5)
	_args[0] = []byte("SetDataItem")
	_args[1] = []byte(access_key)
	_args[2] = []byte(key)
	_args[3] = []byte(value)
	_args[4] = []byte(getDataTypeFromString(data_type))
	return _args
}

func EncodeGetDataItemArgs(access_key string, key string) [][]byte {
	_args := make([][]byte, 3)
	_args[0] = []byte("GetDataItem")
	_args[1] = []byte(access_key)
	_args[2] = []byte(key)
	return _args
}

func DecodeGetDataItemResult(b []byte) (*DataItem, error) {
	var dataItem DataItem
	err := json.Unmarshal(b, &dataItem)
	if err != nil {
		return nil, err
	}
	return &dataItem, nil
}
