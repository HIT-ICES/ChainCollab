# Assertion Coverage Summary

| ID | Dimension | Mode | Targets | Positive | Negative Trigger | Status |
| --- | --- | --- | --- | ---: | ---: | --- |
| SV01 | structural | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV02 | structural | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV03 | structural | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV04 | structural | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV05 | structural | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV06 | structural | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV07 | structural | positive | go,solidity | N/A | N/A | unobserved |
| SV08 | control | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV09 | control | both | go | 100.00% (10/10) | N/A | positive_only |
| SV10 | control | both | solidity | 100.00% (10/10) | N/A | positive_only |
| SV11 | control | both | go | 100.00% (10/10) | N/A | positive_only |
| SV12 | control | both | solidity | 100.00% (10/10) | N/A | positive_only |
| SV13 | control | both | solidity | 100.00% (10/10) | N/A | positive_only |
| SV14 | control | both | go,solidity | 100.00% (10/10) | N/A | positive_only |

## Assertion Notes

- SV01 全局变量应映射到目标语言状态存储结构
- SV02 参与方应映射为访问控制相关结构或检查入口
- SV03 消息应映射为消息处理结构
- SV04 网关应映射为网关相关结构或条件处理入口
- SV05 事件应映射为事件处理结构
- SV06 业务规则应映射为业务规则处理结构
- SV07 预言机任务应映射为预言机任务处理结构
- SV08 Flow 动作应映射为 enable / disable / set 控制代码
- SV09 Go 消息处理函数应包含消息状态推进控制逻辑
- SV10 Solidity 消息处理函数应包含消息状态赋值控制逻辑
- SV11 Go 业务规则处理应存在外部规则调用与继续处理控制证据
- SV12 Solidity 业务规则处理应存在外部规则服务交互控制证据
- SV13 Solidity 业务规则处理应存在结果回写控制证据
- SV14 Flow 条件语义应映射为 compare / parallel 条件检查
