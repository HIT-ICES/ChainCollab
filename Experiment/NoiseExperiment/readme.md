# Noise Experiment 实验手册

## 实验目标

这个目录的实验用于评估一个已经部署好的 BPMN / Choreography 合约在**路径扰动**下的表现。
做法是先准备一条标准执行路径，再自动构造带噪声的执行序列，逐条回放到链上实例中，观察系统对乱序、重复、缺失调用的约束能力。

实验核心关注两件事：

1. 正常路径是否能稳定执行完毕。
2. 扰动路径会被系统接受、在起始阶段拦截，还是在中途失败。


## 整体思路

实验流程可以概括为四步：

1. **加载基线任务**
   - 从输入 JSON 中读取 task。
   - 每个 task 定义 `steps`、`invoke_path`，以及可选的 `appended_index_paths`。
   - `loader.py` 会将其转成内部的 `Task / STEP / CHECK_CONDITION` 结构。

2. **生成带噪路径**
   - `noise_generator.py` 基于标准路径索引生成扰动路径。
   - 支持三类扰动：
     - `add`：重复插入某一步
     - `remove`：删除某一步
     - `switch`：交换两步顺序
   - `main.py` 的 `-N` 用来控制采样比例，本质上是从所有可构造扰动中抽取一部分执行。

3. **创建实例并回放路径**
   - `invoker.py` 先调用 `CreateInstance` 创建链上实例。
   - 然后按路径顺序执行 Event / Gateway / Message / Activity。
   - Message 会根据 `metaInfo` 中定义的字段自动拼装参数。
   - Activity 执行后还会等待 `Avtivity_continueDone` 事件，确认 DMN / 业务规则确实完成。

4. **做状态检查并记录结果**
   - 每一步执行前先做 `pre_check`。
   - 执行后再做 `post_check`。
   - 每条路径的结果会写入输出 JSON，详细日志写入 `*_output.txt`。


## 输入与输出

### 输入任务格式

每个 task 至少包含：

- `name`：任务名
- `steps`：可执行步骤列表
- `invoke_path`：标准路径，对应 `steps` 的索引序列
- `appended_index_paths`：可选，手工补充的额外索引路径

其中每个 step 包含：

- `element_name`：链上元素 ID
- `element_type`：`Message` / `Gateway` / `Event` / `Activity`
- `metaInfo`：消息参数定义，要求是 JSON string
- `parameters`：执行该步时传入的参数
- `invoker`：消息的调用方参与者
- `state_change`：该步执行前后的状态约束

当前目录可参考的输入样例主要在：

- `done/*/basic_path/*.json`
- `path_raw/*.json`

### 输出结果格式

每个 task 下会记录多条路径执行结果。每条结果至少包含：

- `index_path`：执行时采用的步骤索引路径
- `path`：展开后的元素名路径
- `results`：执行结果文本
- `tag`：结果分类

`tag` 的含义来自 `main.py`：

- `0`：`All steps passed`
- `1`：第一步就失败，通常表示扰动路径一开始就违背了使能条件
- `2`：中途失败，说明执行过程中触发了状态不一致或非法路径


## 扰动策略

这里把“噪声”理解为对标准路径做轻量编辑：

- **重复一步**：模拟重复提交、重复触发、消息重放
- **删除一步**：模拟漏发消息、漏执行节点
- **交换顺序**：模拟乱序调用

`main.py` 会先把标准路径本身加入待执行集合，再持续采样扰动路径，直到达到 `-N` 设定的数量。
如果输入中提供了 `appended_index_paths`，这些手工补充的边界路径也会被一并执行。


## 关键脚本

- `main.py`
  - 解析命令行参数
  - 读取输入任务
  - 生成扰动路径
  - 调用执行器并汇总结果

- `loader.py`
  - 把 JSON 任务定义转成内部结构
  - 统一元素类型和状态字符串

- `noise_generator.py`
  - 负责 add / remove / switch 三类路径扰动

- `invoker.py`
  - 创建链上实例
  - 调 FireFly API 执行步骤
  - 监听 websocket 事件
  - 做前置/后置状态检查

- `result_analysis.py`
  - 用于后处理与结果分析

- `FulfillTheRest/extract_from_done.py`
  - 从已有结果中抽取需要补跑的路径

- `FulfillTheRest/merge_into_final.py`
  - 把补跑结果回填到原结果文件中


## 运行方式

1. 创建虚拟环境并安装依赖。
2. 修改 `main.py` 中的参数区，使其指向当前实验部署。
3. 执行实验命令。

示例：

```bash
python3.12 main.py run -input ./done/purchase/basic_path/path1.json -output ./done/purchase/result/path1.json -N 100 -listen
```

常用参数：

- `-input`：单个任务文件或任务目录
- `-output`：输出 JSON 文件
- `-n`：单次噪声生成参数
- `-N`：要执行的扰动路径比例，按百分比计算
- `-m`：扰动模式，默认 `ars`，即 add/remove/switch 全开
- `-e`：只执行默认路径和 `appended_index_paths`，不重新生成随机扰动
- `-listen`：创建 listener 并订阅链上事件；第一次跑新合约通常需要加


## main.py 参数区说明

`main.py` 中有一段需要手工填写的参数区，主要包括：

1. `param`
   - 创建 BPMN 实例前，打开前端 F12。
   - 创建后控制台会打印 `result`，将对应 object 的值填到这里。

2. `url`
   - 格式类似：
   - `http://127.0.0.1:5001/api/v1/namespaces/default/apis/{api-name}`
   - `api-name` 可以在 `127.0.0.1:5001` 的 `interface` 页面查看。

3. `contract_interface_id`
   - 同样在 FireFly 的 `interface` 页面查看。

4. `participant_map`
   - 参与者身份映射，需要到 `127.0.0.1:5001` 的 `identity` 页面获取。

5. `contract_name`
   - 即创建 BPMN 时填写的合约名。


## 判定逻辑

这个实验的判断标准不是“接口调通没调通”，而是“路径是否符合流程状态机”：

- 某一步执行前若目标元素并未使能，`pre_check` 会直接判失败。
- 调用结束后如果状态没有按预期迁移，`post_check` 会判失败。
- 如果是 Activity，还必须收到 `Avtivity_continueDone` 事件。
- 只有整条路径所有步骤都通过，才会被记为 `All steps passed`。

所以，这个实验本质上是在用路径扰动压测 choreograph 合约的状态约束能力。


## 失败路径补跑流程

`release-BlockCollab` 分支新增了一套补跑失败路径的流程，适合在正式实验后重新处理部分异常结果。

### 使用场景

原实验数据中可能存在由于系统不稳定、监听异常或非预期中断导致的失败路径。
这些失败不一定都属于真正的 non-conformance，因此需要把部分路径重新执行。

### 第一步：抽取需要补跑的路径

使用 `FulfillTheRest/extract_from_done.py`，从某个实验目录下的已有结果中抽取 `tag == 1` 的路径。

示例：

```bash
python3 ./FulfillTheRest/extract_from_done.py ./done/blood
```

脚本会在 `basic_path` 中为每个原始路径生成两个文件：

1. `*_patch.json`
   - 在原始 task 上补入 `appended_index_paths`

2. `*_index_mapping_patch.json`
   - 记录这些失败路径在原结果文件中的位置，后续合并结果时会用到

### 第二步：重新运行补丁路径

重新执行时要使用 `-e`，避免再次随机生成大量额外路径。
此时仍然会运行原始默认路径，以及 `appended_index_paths` 中补进去的目标路径。

示例：

```bash
python3 main.py run -input ./done/blood/basic_path/path1_patch.json -output ./done/blood/basic_path/path1_patch_result.json -e -listen
```

### 第三步：合并补跑结果

使用 `FulfillTheRest/merge_into_final.py` 将补跑结果写回原结果文件。

示例：

```bash
python3 ./FulfillTheRest/merge_into_final.py ./done/blood
```

脚本会读取：

- 原结果：`result/*.json`
- 补跑结果：`basic_path/*_patch_result.json`
- 映射关系：`basic_path/*_index_mapping_patch.json`

最终输出 `*_new.json`，用新实验数据覆盖原来失败的部分。


## 注意事项

1. `invoker` 必须与实际参与者身份一致。
2. `metaInfo` 必须是 JSON string，而不是普通 JSON 对象。
3. 如果涉及 `Activity`，要确认前置 message 的输入满足 DMN 所需字段，并能产出后续网关使用的结果。
4. Activity 类型必须写成 `Activity`，不要写成 `businessRule`。
5. listener 的监听通常需要在 `5001` 端口侧建立，否则可能收不到创建事件。
6. 每次跑新文件前，最好先处理掉 websocket 中未消费的历史事件；同一个事件通常只能消费一次。
7. URL 中端口号要和实际发起操作的 org 对应的 FireFly 端口一致。
8. 系统本身存在一定不稳定性，补跑一次后仍可能存在失败，需要多轮处理。
9. 准备基线路径时，最好检查 BPMN 是否有冗余元素，否则状态检查和真实执行可能不一致。

如果异常终止，可能需要手动消费 websocket 消息，例如连接：

```text
ws://localhost:5001/ws
```

订阅消息示例：

```json
{"type":"start","name":"InstanceCreated-manu1","namespace":"default","autoack":true}
{"type":"start","name":"Avtivity_continueDone-manu1","namespace":"default","autoack":true}
```
