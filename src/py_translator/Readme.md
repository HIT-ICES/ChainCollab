存在问题Done：：
~~1. 目前globalValiable是否是结合了DMN中的元素确定的，还是在按照原来的逻辑从序列流上判断？~~

~~2. invoke other chaincode 的name，目前写死，assert:v1   要么指定为固定的，要不通过参数传进来~~

[x] ffi  多出这个格式
                [
                    "error",
                    "boolean"
                ]

4. [x] 优化initParameter结构，不暴露cid hash
5. fmt.Error 在return之后，不打印日志，在返回之前打印
6. [x] instanceIDByte, err := stub.GetState("currentInstanceID")
7. [x] 读取instance ID的时候，不需要unmarshal
	fmt.Print("instanceIDString: ", instanceIDByte)
	instanceID = string(instanceIDByte)
	fmt.Print("instanceID: ", instanceID)
8. 把createMessage，CreateParticipant等改成不断往json续拼凑字段 doing~!


TODO：
1. CreateInstance 阶段setEvent  instanceID
2. 