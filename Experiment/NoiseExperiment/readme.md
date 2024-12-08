# 实验手册


## 概要



## 主要流程

1.  创建venv, pip install

2.  main.py的参数

   （1）param : 创建bpmn实例前，直接打开F12，创建后f12控制台会打印result,点击赋值result的object

   （2）url: "http://127.0.0.1:5001/api/v1/namespaces/default/apis/{访问127.0.0.1:5001,在interface里有名字，如manu1-1cb94f}"

   （3）contract_interface_id：同上interface

   （4）participant_map： 访问127.0.0.1:5001，在identity里

   （5）contract_name：就是创建bpmn时你填的名字

​      
3. 执行：python3.12 main.py run -input {.../.../path1.json} -output {.../.../path1.json} -N 100 -listen

   * 第一次要加-listen     -N为生成路径的百分比
   * 注意异常终止时，要通过websocket消费掉message,用google插件。 ws://localhost:5001/ws；{"type": "start", "name": "InstanceCreated-manu1", "namespace": "default", "autoack": true}；{"type": "start", "name": "Avtivity_continueDone-manu1", "namespace": "default", "autoack": true}。


   ​

## 补充实验要点 2024-12-8

### 起因

原实验数据中存在非Conformance与Non-Conformance导致的中断，因此需要重新运行部分path。

### 方案

#### 获取需要重跑内容

实验中生成的path为随机生成，因此仅能从过去实验结果中抽取失败的path。

使用FulfillTheRest文件夹下的extract_from_done.py脚本，从结果中抽取出需要重跑的路径。

```sh
python3 extract_from_done.py /home/qkl02-ljl/code/IBC/Experiment/NoisExperiment/done/blood
```
注意，此处以文件夹为抽取与合并单位，而非path.json文件。

这样会在basic_path中对每一个path生成两个文件：

1. path_index_mapping_patch.json: 用于记录失败路径对应实验结果文件中的序号
2. path_patch.json: 使用失败路径填写了appended_index_paths 字段的原始path

#### 重新运行

与正式实验相同，需要启动区块链环境，部署合约，收集相关信息，粘贴到main.py指定处，然后运行。

需要注意的参数：注意URL中的端口号，是否与参与操作的用户所属org的firefly端口相同；以及listener的监听需要在5001进行（需要如此才能监听到创建事件）。

注意，此时执行需要使用 -e 参数，屏蔽额外的路径生成（但仍然会运行原始路径中的默认路径，即conformance的路径）。

```sh
python3 main.py run -input ./done/blood/basic_path/path1_patch.json -output ./done/blood/basic_path/path1_patch_result.json -e -listen
```

此后，得到path_patch_result.json文件

#### 合并实验结果

使用FulfillTheRest文件夹下的merge_into_final.py脚本，将新的实验结果合并成新的完整实验结果。

```sh
python3 merge_into_final.py /home/qkl02-ljl/code/IBC/Experiment/NoiseExperiment/done/blood
```

这将生成path_new.json文件，其中使用新的实验数据覆盖了原先数据中失败的部分。

#### 注意事项

由于系统的不稳定性，新的数据中仍旧会存在部分失败，因此，以上内容可能需要多次执行。

为方便文件的管理，可以自行修改脚本中的新文件命名规则与目录，但注意对齐两个脚本。