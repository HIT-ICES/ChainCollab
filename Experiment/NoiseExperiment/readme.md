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

 