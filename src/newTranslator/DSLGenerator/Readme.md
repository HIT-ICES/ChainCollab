存在问题Done：：
~~1. 目前globalValiable是否是结合了DMN中的元素确定的，还是在按照原来的逻辑从序列流上判断？~~

~~2. invoke other chaincode 的name，目前写死，assert:v1   要么指定为固定的，要不通过参数传进来~~

3. [x] ffi  多出这个格式
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
9. [x] service.py,能够根据BPMN content返回有几个Activity的id及name
10. [x] 根据DMN content获取decisionID，目前Java链码有写，是不是再用python写个方法，放在server.py里？
11. [x] 目前无法通过getAllMessage获取所有的message,因为需要实例ID查询消息。此处应该通过BPMN内容提取出所有消息的properties字段

TODO：
1. CreateInstance 阶段setEvent  instanceID
2. 