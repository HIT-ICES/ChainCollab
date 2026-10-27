from pathlib import Path
import os,sys,json,subprocess,ast,re,csv,shutil,hashlib,zipfile,xml.etree.ElementTree as ET
R=Path('/home/shenxz-lab/code/ChainCollab');os.chdir(R);sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();A=R/'artifacts'/('TSC_SecIV_DevFork_Evidence_'+sha[:8]);N='Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn';D='Experiment/BPMNwithDMNcase/new/supplyChainPaper.dmn';T='src/newTranslator/generator/translator.py';P='src/newTranslator/generator/parser/choreography_parser/parser.py';G='src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py';S='src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py';GT='src/newTranslator/CodeGenerator/b2cdsl-go/templates/contract.go.jinja';ST='src/newTranslator/CodeGenerator/b2cdsl-solidity/templates/contract.sol.jinja';AB='src/bpmn-chor-app/src/modeler/moddle/abc.json'
def write(p,s):
 p=A/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def txt(p):return (R/p).read_text(encoding='utf-8')
def line(p,v):return next((i for i,l in enumerate(txt(p).splitlines(),1) if v in l),0)
def ref(p,v):return f'`{p}:{line(p,v)}` (`{v}`, commit `{sha}`)'
def block(p,i,j,lang=''):
 return f'原始摘录：`{p}:{i}`，commit `{sha}`\n\n```{lang}\n'+'\n'.join(txt(p).splitlines()[i-1:j])+'\n```\n'
def method(p,name):
 n=next(n for n in ast.walk(ast.parse(txt(p))) if isinstance(n,ast.FunctionDef) and n.name==name);return block(p,n.lineno,n.end_lineno,'python')
def xml(id):
 s=txt(N);m=re.search(r'<(bpmn2:\w+)\b[^>]*\bid="'+re.escape(id)+r'"[^>]*',s)
 if not m:return ''
 end=s.index('>',m.start())+1
 if s[end-2:end]!='/>' :end=s.index('</'+m.group(1)+'>',end)+len(m.group(1))+3
 return 'XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：'+ref(N,'id="'+id+'"')+'\n\n```xml\n'+s[m.start():end]+'\n```\n'
def fun(folder,ext,name):
 p=str((A/folder/('SupplyChainPaper.'+ext)).relative_to(R));ls=txt(p).splitlines();pat=(r'^func \(cc \*SmartContract\) ' if ext=='go' else r'^    function ')+re.escape(name)+r'\('
 i=next((i for i,l in enumerate(ls) if re.search(pat,l)),None)
 if i is None:return '没有生成 '+name+' 函数。\n'
 j=next(j for j in range(i+1,len(ls)) if ls[j]==('}' if ext=='go' else '    }'));return block(p,i+1,j+1,ext)
h=f'基准：dev-MultiBlockChain-fork，commit `{sha}`；日期 2026-10-27（Asia/Shanghai）。生成成功不代表部署或 DMN 执行成功。\n\n'
dsl=(A/'generated_pim/SupplyChainPaper.b2c').read_text();fc=json.loads((A/'generation_contexts/fabric.diagnostic.json').read_text());sc=json.loads((A/'generation_contexts/geth.diagnostic.json').read_text())
for p in [R/'src/bpmn-chor-app/src/ChorModelerApp.tsx',*(R/'src/bpmn-chor-app/src/modeler').rglob('*.tsx')]:
 dest=A/'source_references'/p.relative_to(R);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
sys.path.insert(0,str(R/'src/newTranslator'));from generator.translator import GoChaincodeTranslator
opened=[]
def audit(event,args):
 if event=='open' and args and isinstance(args[0],(str,bytes)):
  q=os.fsdecode(args[0])
  if q.startswith(str(R)) and '__pycache__' not in q:opened.append(q)
sys.addaudithook(audit)
x=GoChaincodeTranslator(bpmn_file=str(R/N));repeat=x.generate_chaincode();write('logs/cim_read_audit.json',json.dumps({'kind':'diagnostic rerun, original translator, no patch','opened_paths':sorted(set(opened)),'native_equal':repeat==dsl,'sidecar_dmn_opened':str(R/D) in opened},indent=2))
old=GoChaincodeTranslator(bpmn_file=str(R/'Experiment/BPMNwithDMNcase/SupplyChainPaper.bpmn')).generate_chaincode();write('generated_pim/legacy_source_current_translator.b2c',old);write('logs/new_legacy_comparison.json',json.dumps({'same_bytes':dsl==old,'note':'both generated with current HEAD; not historical outputs'},indent=2))
rows=[]
for p in (A/'source_references').rglob('*.py'):
 for n in ast.walk(ast.parse(p.read_text())):
  if isinstance(n,(ast.FunctionDef,ast.ClassDef)):rows.append([p.relative_to(A/'source_references').as_posix(),n.name,n.lineno,n.end_lineno,sha])
with (A/'source_references/symbol_locations.csv').open('w',newline='') as f:w=csv.writer(f);w.writerow(['path','symbol','line','end_line','commit']);w.writerows(rows)
root=ET.parse(R/N).getroot();local=lambda e:e.tag.split('}')[-1];counts={k:sum(local(e)==k for e in root.iter()) for k in ['participant','message','messageFlow','businessRuleTask','exclusiveGateway','parallelGateway','startEvent','endEvent','documentation','extensionElements']};write('source_models/inventory.json',json.dumps(counts,indent=2))
write('01_CIM_EXTENSION_MODEL.md',h+'''已落地的扩展机制为 BPMN extensionElements + abc 自定义命名空间 + bpmn-moddle descriptor；未发现该机制独立 XSD。descriptor 有六个 Element 子类。

| 宿主 | 扩展标签 | 属性 | PIM 去向 |
|---|---|---|---|
| message | MessageSchema/Property | name,type,description,required,definition | Message.schema；标量推导 GlobalVar |
| message | MessageSchema/File | name,type,description,required,definition | schema.files；本例文件未进入 globals |
| businessRuleTask | BusinessRule/Input, Output | name,type,description,definition | BusinessRule ParamMapping，globals |

MessageSchema 的 properties/files 和 BusinessRule 的 inputs/outputs 为多值包含关系。definition 属性仍装 JSON，并未彻底消除 JSON。规则解析以 JSON 为基础 setdefault name/type/description，重复字段冲突时 definition 内值优先；消息类似。

Participant、MessageFlow、ChoreographyTask、Gateway、SequenceFlow 没有该 descriptor 的专用扩展类型。Participant 用标准 name/ID/multiplicity；MessageFlow sourceRef/targetRef/messageRef、Task participantRef/messageFlowRef、SequenceFlow sourceRef/targetRef/conditionExpression 均使用标准结构。身份由 bindings.json 或默认值提供。

扩展没有实际 DMN resource/decision 引用或独立 globalRef；I/O 用 name 推导首字母大写的 global。解析器按 local-name 匹配，没有严格核验 abc namespace；扩展优先，缺失扩展时 documentation 回退。读取后转成内部兼容 JSON，再进入原有转换器。

'''+ref(AB,'"name": "MessageSchema"')+'\n\n'+method(P,'_read_message_schema_extension')+method(P,'_read_business_rule_extension')+block(P,line(P,'case NodeType.MESSAGE.value:'),line(P,'case NodeType.RECEIVE_TASK.value:'),'python')+xml('Message_0rwz1km')+xml('Activity_0rm8bkp'))
write('02_SUPPLYCHAIN_SOURCE_STATUS.md',h+f'''此前已汇总：f98238e8:docs/SupplyChainPaper/SupplyChainPaper_20260922_133943/。本分支工作树没有该目录；历史 README/issues/status/provenance/traceability/worked_mapping 用 git show 保存到 source_references/historical_f98238e8/，不把旧 XML 当成新扩展证据。

本轮主输入为用户指定 `{N}`。统计：{json.dumps(counts)}。

新版 SupplyChainPaper 的所有消息 schema 和 Priority Decision I/O 已迁移。上级目录旧同名 BPMN 与两版 DMN 原样保存在 source_models/；原始模型不改动。Activity_0rm8bkp 有 numberOfUnits/urgent/supplierReputation 输入及 finalPriority 输出，但没有 dmnResource/decisionID 属性。name 到 global 的映射由转换器推导。

相关 DMN 真实决策为 decision_0tybghz 和 Decision_0zwjfyy，后者 requiredDecision 指向前者。CIM→PIM 没读取该 DMN 文件；静态调用链与 logs/cim_read_audit.json 的实际读取审计一致，审计重跑的 DSL 与原生 CLI byte-equal。

模型接口迁移已完成；若要声称显式 DMN 引用已完成，仍缺模型字段、解析逻辑和真实运行配置核验。本轮不修复。

'''+xml('Activity_0rm8bkp')+block(D,70,76,'xml'))
write('03_CIM_TO_PIM_TRACE.md',h+'''原生 CIM→PIM PASS；当前 textX grammar 解析 PASS。完整命令/输出/退出码在 logs/cim_to_pim.*；生成完整原文位于 generated_pim/SupplyChainPaper.b2c。使用已有 .venv，未修改或安装依赖。

链路：Choreography._parse_node → MessageCatalog / ParameterExtractor → DSLContractBuilder → FlowPlanner。参与方身份来自 ParticipantMetadataResolver 的 bindings/default；端点来自 messageFlow；schema 来自 abc 扩展转成的内部 JSON；globals 从消息 properties、规则 I/O、条件变量提取，number→int、boolean→bool；文件保留 schema，不推导为本例 globals。

BusinessRule 字段来源：dmnResource=<taskID>.dmn；decisionID=<taskID>_DecisionID（均为命名约定）；inputMappings/outputMappings 为接口 name→public_the_name(name)；initialState=INACTIVE（默认）；RuleFlow 来自后继关系。Start READY，其余本例元素 INACTIVE。旁边 DMN 的规则和决策依赖未展开为 PIM。

'''+method(T,'_build_business_rules_section')+method(T,'_business_rule_flows')+method(T,'_parallel_join_flows')+'完整原始 DSL：\n\n```text\n'+dsl+'\n```\n')
write('05_PSM_AND_TEMPLATE_ARCHITECTURE.md',h+'''没有独立 PSM 元模型、原生 PSM 文件或外置 platform profile 文件。平台具体化分布于 Python 类型映射/state alias、adapter、renderer、Jinja 主/子模板及内置 runtime/helper。两份 context JSON 为本次诊断，不能宣称为原生 PSM。

Fabric context keys：'''+', '.join(fc)+'''。

Geth context keys：'''+', '.join(sc)+'''。

globals/participants/messages 等为属性映射及类型具体化；flow_functions 和 done_actions 已是平台代码字符串。Go business_rules payload 仅 name/done_actions；不把 PIM input/outputMappings 逐字段展开，而依赖初始化 ParamMapping。Solidity payload 将 I/O 具体化为 param_literal/slot_name/sol_type，用于静态输入构造和输出写回。

Fabric 消息、事件、gateway 的函数使用 Jinja 子模板；规则 Request/Continue、Participant、globals/初始化在 contract.go.jinja。Geth 消息、事件、gateway 使用 Python f-string 函数骨架，主模板插入 flow_functions；规则 Request/Continue 和结构初始化在 contract.sol.jinja。Gateway 模式共用 handler 形状；顺序 flow 只是函数中的状态更新；并非每个源对象生成一函数。

诊断调用未经修改的 build_context 和原模板 render，与两平台原生 textX CLI 输出均 byte-identical，详见 logs/stage_status.json。没有人为新建 PSM 格式或替换生成行为。

'''+method(G,'build_context')+method(S,'build_context')+method(G,'_business_rule_payload')+method(S,'_business_rule_payload')+method(S,'_render_messages'))
spec=[
('Structure & Data','S1','Participant and identity binding','Participant_0w6qkdf','participant Participant_0w6qkdf','Participant/InitParameters/CreateInstance','ParticipantInit/_createParticipant','_build_participants_section','_create_instance_payload','_participant_payload'),
('Structure & Data','S2','Message interface','Message_0rwz1km','message Message_0rwz1km','Message_0rwz1km_Send / Message_0rwz1km_Complete','Message_0rwz1km_Send','_build_messages_section','_render_messages','_render_messages'),
('Structure & Data','S3','Shared data','Message_0rwz1km','NumberOfUnits: int','StateMemory.NumberOfUnits / Send assignment','StateMemory.NumberOfUnits / Send assignment','_build_globals_section','_state_memory_fields','_global_variables'),
('Business Rules','B1','BusinessRuleTask interface and request','Activity_0rm8bkp','businessrule Activity_0rm8bkp','Activity_0rm8bkp','Activity_0rm8bkp','_build_business_rules_section','_business_rule_payload','_business_rule_payload'),
('Business Rules','B2','BusinessRuleTask completion and continuation','Activity_0rm8bkp','when businessrule Activity_0rm8bkp done','Activity_0rm8bkp_Continue','Activity_0rm8bkp_Continue','_business_rule_flows','rule_done_actions','rule_done_actions'),
('Events & Sequencing','E1','Events and sequence relations','Event_06sexe6','start event Event_06sexe6 enables Message_1wswgqu','Event_06sexe6 / Message_1wswgqu_Complete / Event_13pbqdz','Event_06sexe6 / Message_1wswgqu_Send / Event_13pbqdz','_start_event_flows','_render_start_events','_render_start_events'),
('Gateways','G1','Exclusive split','Gateway_0ep8cuh','when gateway Gateway_0ep8cuh completed','Gateway_0ep8cuh','Gateway_0ep8cuh','_gateway_flows','_render_gateways','_render_gateways'),
('Gateways','G2','Parallel split','Gateway_0onpe6x','when gateway Gateway_0onpe6x completed','Gateway_0onpe6x','Gateway_0onpe6x','_gateway_flows','_render_gateways','_render_gateways'),
('Gateways','G3','Parallel join','Gateway_1fbifca','parallel gateway Gateway_1fbifca await','Gateway_1fbifca','Gateway_1fbifca','_parallel_join_flows','_parallel_guard_block','_parallel_guard_block')]
md=h+'九项均在当前 SupplyChainPaper 中实际存在。源码位置、commit、生成单元见 CSV；完整函数摘录见下文及 06/07。\n\n| Category | Item | CIM | PIM | Fabric | Geth |\n|---|---|---|---|---|---|\n';mr=[]
for cat,key,title,id,pim,go,sol,tm,gm,sm in spec:
 row={'category':cat,'item':key,'description':title,'commit':sha,'cim_path':N,'cim_id':id,'cim_line':line(N,'id="'+id+'"'),'pim_path':'generated_pim/SupplyChainPaper.b2c','pim_locator':pim,'pim_line':next(i for i,l in enumerate(dsl.splitlines(),1) if pim in l),'fabric_units':go,'geth_units':sol,'translator':f'{T}:{line(T,"def "+tm)}','fabric_renderer':f'{G}:{line(G,"def "+gm)}','geth_renderer':f'{S}:{line(S,"def "+sm)}','fabric_generated':'generated_fabric/SupplyChainPaper.go','geth_generated':'generated_geth/SupplyChainPaper.sol','fabric_template':GT,'geth_template':ST};mr.append(row)
 md+=f'| {cat} | {key} {title} | {id} (L{row["cim_line"]}) | {pim} (L{row["pim_line"]}) | {go} | {sol} |\n'
with (A/'04_TRANSFORMATION_MATRIX.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=mr[0]);w.writeheader();w.writerows(mr)
md+='\nS1/S3 对应结构与初始化；B1/B2 对应两个函数；E1 顺序关系包含嵌入动作；G1/G2/G3 复用 handler 加分支/并行代码。\n'
for cat,key,title,id,pim,go,sol,tm,gm,sm in spec:
 md+='\n## '+key+' '+title+'\n\n'+xml(id)+ref(T,'def '+tm)+'\n\n'+ref(G,'def '+gm)+'\n\n'+ref(S,'def '+sm)+'\n\n'
 if key in ['S1','S3']:md+=method(G,gm)+method(S,sm)
 elif key not in ['B1','B2']:md+=fun('generated_fabric','go',go.split(' / ')[0])+fun('generated_geth','sol',sol.split(' / ')[0])
 else:md+='模板与生成函数原始摘录见 06。\n'
write('04_TRANSFORMATION_MATRIX.md',md)
body=h+'''## Stage 1 CIM

贯穿对象为 Priority Decision Activity_0rm8bkp。接口已迁移，但没有显式 DMN 引用。DMN 中 Decision_0zwjfyy 依赖 decision_0tybghz；PIM 合成 decisionID 与它们不同。

'''+xml('Activity_0rm8bkp')+xml('Flow_1jxt9fr')+'\n## Stage 2 PIM\n\n'
pimrel=str((A/'generated_pim/SupplyChainPaper.b2c').relative_to(R));body+=block(pimrel,line(pimrel,'businessrule Activity_0rm8bkp'),line(pimrel,'    oracletasks'),'text')+block(pimrel,line(pimrel,'when businessrule Activity_0rm8bkp done'),line(pimrel,'when businessrule Activity_0rm8bkp done')+2,'text')
body+='''输入 globals：NumberOfUnits:int、Urgent:bool、SupplierReputation:int；输出 FinalPriority:string。RuleFlow 只启用 Gateway_0ep8cuh，不赋值；该 gateway 读取 FinalPriority 并判断 Low/High/Medium/VeryLow。

## Stage 3 Fabric specialization

请求函数查询 Oracle:v1/default 的 CID，发 DMNContentRequired，进入 WAITINGFORCONFIRMATION。Continue 显式接收 ContentOfDmn、校验 hash、根据 runtime ParamMapping 反射读取共享状态，调用 DMNEngine:v1/default 的 createRecord，反射写回 output 数组、置 COMPLETED，并执行 done_actions 启用后继。此平台没有 Geth requestId 协议。

Go context 未将 PIM I/O 映射逐字段展开；ParamMapping、DecisionID、DMN content 依赖 InitParameters。运行时同一 map 同时用于输入和输出，配置正确性仍待验证。不能声称 Go 自动落实了全部 PIM 参数映射。

真实诊断 context 精选：

```json
'''+json.dumps({'business_rules':fc['business_rules'],'init_params':[v for v in fc['init_params'] if 'Activity_0rm8bkp' in v['name']]},ensure_ascii=False,indent=2)+'\n```\n'+fun('generated_fabric','go','Activity_0rm8bkp')+fun('generated_fabric','go','Activity_0rm8bkp_Continue')
body+='''\n## Stage 4 Geth specialization

requestDMNDecision(evalUrl,CID,decisionId,inputData) 返回 requestId，持久化后 WAITING_FOR_CONFIRMATION；Continue 检查 getRequestStatus 的 requester/state，再 getRawByRequestId；按 output_mappings 读 finalPriority 写 FinalPriority，置 COMPLETED 并启用后继。Continue 只接收 instanceId，不接收 ContentOfDmn。

真实诊断 context 精选：

```json
'''+json.dumps(sc['business_rules'],ensure_ascii=False,indent=2)+'\n```\n'+fun('generated_geth','sol','Activity_0rm8bkp')+fun('generated_geth','sol','Activity_0rm8bkp_Continue')
body+='''\n## Stage 5 原始模板展开

Geth：PIM numberOfUnits→NumberOfUnits → input_mappings[param_literal,slot_name,sol_type=int256] → mapping.param_literal / mapping.slot_name / mapping.sol_type → _jsonInt(inst.stateMemory.NumberOfUnits)。finalPriority→FinalPriority → output_mappings → _extractJsonString(raw,"finalPriority")。RuleFlow → rule_done_actions → business_rules[].done_actions → {{ rule.done_actions }} → Gateway_0ep8cuh ENABLED。

Fabric：RuleFlow → rule_done_actions → business_rules[].done_actions → {{ rule.done_actions }} → cc.ChangeGtwState(...,ENABLED)。输入输出是 runtime ParamMapping 的反射循环，没有 Geth 的逐字段映射占位符。

'''+block(GT,947,1134,'jinja')+block(ST,715,800,'jinja')
write('06_BUSINESSRULE_WORKED_MAPPING.md',body)
body=h+'本例具备全部模式。以下代码块为原始摘录，保留源定位。PIM 摘录是相关行索引；完整声明/flow 见 03。\n'
for title,id,fs in [('Participant and message','Message_1wswgqu',['Message_1wswgqu_Send','Message_1wswgqu_Complete']),('Schema and globals','Message_0rwz1km',['Message_0rwz1km_Send','Message_0rwz1km_Complete']),('Start and sequence','Event_06sexe6',['Event_06sexe6']),('Exclusive','Gateway_0ep8cuh',['Gateway_0ep8cuh']),('Parallel split','Gateway_0onpe6x',['Gateway_0onpe6x']),('Parallel join','Gateway_1fbifca',['Gateway_1fbifca'])]:
 body+='\n## '+title+'\n\n'+xml(id)
 if title.startswith('Participant'):body+=xml('Participant_0w6qkdf')
 body+='PIM 原始行摘录（含行号）：\n\n```text\n'+'\n'.join(f'{i}: {l}' for i,l in enumerate(dsl.splitlines(),1) if id in l or ('NumberOfUnits' in l and title.startswith('Schema')))+'\n```\n'
 for f in fs:
  body+=fun('generated_fabric','go',f)
  if not f.endswith('_Complete'):body+=fun('generated_geth','sol',f)
 gm='_render_messages' if title.startswith(('Participant','Schema')) else ('_render_start_events' if title.startswith('Start') else '_render_gateways');body+=ref(G,'def '+gm)+'\n\n'+ref(S,'def '+gm)+'\n'
write('07_OTHER_PATTERN_EXAMPLES.md',body)
write('08_VERSION_DIFF_AND_LIMITATIONS.md',h+'''历史归档在 f98238e8 的 docs/SupplyChainPaper/；本轮保存历史摘录，并重新跑新版模型，没有拼接未经执行的转换链。两个比较基准的完整 git diff 见 logs/diff_f98238e8.stdout 和 logs/diff_release-MultiBlockchain.stdout。

- 新增 abc descriptor、新版 BPMN/DMN 样例和解析器扩展读取。前端 MessageModal/DmnModal 写扩展，ChorModelerApp 注册 moddle；原文件已保存。
- documentation 没有全局移除：message/businessRule 扩展优先、缺失回退，Oracle/split 的文档兼容路径仍在。definition 属性中继续有 JSON。
- 对 f98238e8，translator.py/grammar 未改变；BusinessRule/DMN 资源名及 decision ID 推导未变；Go renderer 把 Send 后 COMPLETED 改为 WAITINGFORCONFIRMATION。Jinja 模板/Solidity renderer 未改。release 比较的核心修改也在 parser 和 Go renderer，具体以原始 diff 为准。
- 旧函数/模板证据经当前 HEAD 核对可作参考；旧 documentation XML 不能作为新扩展证据。generated_pim/legacy_source_current_translator.b2c 是旧模型用当前转换器重新生成，并非历史产物；比较见 new_legacy_comparison.json。

实现边界和问题：

1. DMN ID 不匹配仍存在：PIM 合成 Activity_0rm8bkp.dmn / Activity_0rm8bkp_DecisionID；实际 supplyChainPaper.dmn 决策为 decision_0tybghz、Decision_0zwjfyy。CIM→PIM 不读 requiredDecision。DMN 服务执行 NOT_RUN。
2. Fabric 消息闭环的旧状态问题已在源码修正：Send→WAITINGFORCONFIRMATION；Complete→COMPLETED，完成后激活后继。此为静态/生成证据，没有链上事务验证。
3. Geth 仍是单 Send→COMPLETED，没有 Complete；不能声称与 Fabric 有相同接收确认协议。
4. 并行 join 检查 Message_0cba4t6 和 Message_0pm90nx 均 COMPLETED。guard 在 gateway 完成和后继启用前；前驱只 enable gateway，仍需调用它。未做并发链上执行测试。
5. Go 规则 I/O 依赖 runtime ParamMapping；context 未消费 PIM I/O 逐字段展开。Continue 多处错误返回可能被覆盖/未立即返回（GetInstance、Invoke_Other_chaincode、SetGlobalVariable）；不能以成功展开证明正确执行。
6. number→int；文件只保留 schema；required/复杂 schema 保留不代表全部运行时验证。namespace 按 local-name 匹配，不是 XSD 校验。
7. 平台编译、部署、真实身份配置、Oracle/DMNEngine/IDmnLite 调用均 NOT_RUN。生成 PASS 不能证明 DMN 绑定有效、平台行为等价或运行成功。

初始 tracked 修改为空；src/backend/api/ 与 src/java-env-custom-image/ 为既有未跟踪项。本轮只新增 artifacts，未改现有模型/grammar/转换器/生成器/模板/论文，未提交 Git。

'''+method(G,'_parallel_guard_block')+method(S,'_parallel_guard_block'))
for p in [GT,ST,*[str(p.relative_to(R)) for p in (R/'src/newTranslator/CodeGenerator/b2cdsl-go/templates/flows').glob('*.jinja')]]:
 dest=A/'template_extracts'/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/p,dest)
write('template_extracts/README.md','此目录为原始完整模板副本；06/07 为精选原始片段。Python renderer 原文件在 source_references；精确行号在 symbol_locations.csv。\n')
status=json.loads((A/'logs/stage_status.json').read_text());status.update({'fabric_compile':'NOT_RUN','geth_compile':'NOT_RUN','deployment_and_dmn_runtime':'NOT_RUN','audit_native_equal':repeat==dsl});write('logs/stage_status.json',json.dumps(status,indent=2))
write('00_START_HERE.md',h+'''此前做过：f98238e8 中有 2026-09-22 SupplyChainPaper 归档。本次依据用户指定 new/SupplyChainPaper.bpmn 重新取证；new/supplyChainPaper.dmn 只是相关模型，不是本次 CIM→PIM 的实际输入。

| 阶段 | 状态 |
|---|---|
| 新结构化扩展 | CONFIRMED：消息 schema、规则 I/O |
| 原生 CIM→PIM | PASS |
| 当前 textX grammar 解析 | PASS |
| Fabric/Go 原生生成 | PASS |
| Geth/Solidity 原生生成 | PASS |
| 诊断 context 展开对比原生结果 | PASS：两端 byte-identical |
| 平台编译、部署、实际 DMN 执行 | NOT_RUN |

01 扩展模型；02 新旧源状态；03 CIM→PIM；04 九项矩阵（含 CSV）；05 暂态 context/模板架构；06 BusinessRule 贯穿；07 其他模式；08 版本差异/边界。

关键边界：DMN 资源/decision ID 为合成值，与原始 DMN 不匹配；没有独立原生 PSM 或外置 platform profile；Go 参数映射依赖初始化；消息/决策请求协议两平台不同。完整 PIM/context/template/function 生成证据已获得，真实 DMN 运行闭环未验证。

source_models 为原始 CIM/DMN；generated_* 为本轮原生输出；generation_contexts 为非原生诊断；source_references 包含当前源码和隔离的历史摘录；logs 记录命令、版本、退出码、读取审计及复现脚本。manifest.csv 保存来源、commit、SHA256。未采集 bindings 内容、私钥、口令或敏感部署配置。

review_bundle/ 为精选审阅包，review_bundle.zip 为 ZIP。完整产物保留主归档。
''')
print('Documents generated',counts)
