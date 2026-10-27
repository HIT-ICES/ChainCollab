from pathlib import Path
import os,sys,subprocess,json,csv,hashlib,shutil,zipfile,importlib
R=Path('/home/shenxz-lab/code/ChainCollab');os.chdir(R);sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();A=R/'artifacts'/('TSC_SecIV_DevFork_Evidence_'+sha[:8]);GT='src/newTranslator/CodeGenerator/b2cdsl-go/templates/contract.go.jinja';ST='src/newTranslator/CodeGenerator/b2cdsl-solidity/templates/contract.sol.jinja'
def write(p,s):q=A/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(s,encoding='utf-8')
def loc(p,s):return next((i for i,l in enumerate(p.read_text().splitlines(),1) if s in l),0)
def add(p,s):q=A/p;q.write_text(q.read_text()+s,encoding='utf-8')
# Precise generated/template locations in the machine readable matrix.
f=A/'04_TRANSFORMATION_MATRIX.csv';rows=list(csv.DictReader(f.open(encoding='utf-8-sig')))
for r in rows:
 k=r['item'];g=A/r['fabric_generated'];s=A/r['geth_generated']
 if k=='S1':gn='type Participant struct';sn='struct Participant';gt='type Participant struct';st='struct Participant'
 elif k=='S3':gn='NumberOfUnits int';sn='int256 NumberOfUnits';gt='type StateMemory struct';st='struct StateMemory'
 else:
  name=r['fabric_units'].split(' / ')[0];gn=') '+name+'(';sn='function '+r['geth_units'].split(' / ')[0]+'('
  gt='{{ rule.name }}_Continue' if k=='B2' else ('{{ rule.name }}(ctx' if k=='B1' else '')
  st='{{ rule.enum_name }}_Continue' if k=='B2' else ('{{ rule.enum_name }}(uint256' if k=='B1' else '{{ function }}')
 if k=='S3' and not loc(g,gn):gn='NumberOfUnits'
 r['fabric_generated_line']=loc(g,gn);r['geth_generated_line']=loc(s,sn)
 if k in ['S2','E1','G1','G2','G3']:
  sub={'S2':'message_send','E1':'start_event','G1':'gateway','G2':'gateway','G3':'gateway'}[k];r['fabric_template']=f'src/newTranslator/CodeGenerator/b2cdsl-go/templates/flows/{sub}.go.jinja:1'
  r['geth_template']='Python skeleton: '+r['geth_renderer']+'; '+ST+':'+str(loc(R/ST,'{{ flow_functions'))
 else:
  r['fabric_template']=GT+':'+str(loc(R/GT,gt));r['geth_template']=ST+':'+str(loc(R/ST,st))
with f.open('w',newline='',encoding='utf-8-sig') as out:w=csv.DictWriter(out,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
# Explicitly preserve diagnostic failure, distinguish from corrected final run.
write('logs/README.md','stage_status.json 是最终状态。diagnostic_error.txt 保留第一次诊断脚本调用 LanguageDesc 的失败；随后改为直接加载当前 grammar，已成功重跑。该失败不是原生转换器失败。原生 CLI 的 command.json/stdout/stderr 独立记录。collect_seciv.py/document_seciv.py 为旁路复现脚本，不是产品代码。平台编译与部署均 NOT_RUN。\n')
for p in ['collect_seciv.py','document_seciv.py']:
 shutil.copy2(R/'artifacts'/p,A/'logs'/p)
shutil.copy2(Path(__file__),A/'logs/finalize_seciv.py')
# Record resolved module paths to prove current checkout used.
for d in ['src/newTranslator','src/newTranslator/DSL/B2CDSL','src/newTranslator/CodeGenerator/b2cdsl-go','src/newTranslator/CodeGenerator/b2cdsl-solidity']:sys.path.insert(0,str(R/d))
mods={m:str(Path(importlib.import_module(m).__file__).resolve()) for m in ['generator.translator','b2cdsl','b2cdsl_go','b2cdsl_solidity']};write('logs/resolved_modules.json',json.dumps(mods,indent=2))
for p in ['00_START_HERE.md','02_SUPPLYCHAIN_SOURCE_STATUS.md','08_VERSION_DIFF_AND_LIMITATIONS.md']:
 add(p,'\n本轮补充核验：旧模型和新模型分别用当前 HEAD 转换，生成 DSL 逐字节相同（logs/new_legacy_comparison.json）。这说明本例接口迁移保留了原转换输出，不代表真实 DMN 引用已增加。\n')
for p in ['08_VERSION_DIFF_AND_LIMITATIONS.md']:
 q=A/p;t=q.read_text().replace('前端 MessageModal/DmnModal 写扩展，ChorModelerApp 注册 moddle','前端 MessageModal/DmnModal 编辑接口，ChorModelerApp 构造/迁移扩展并注册 moddle');q.write_text(t,encoding='utf-8')
ui='src/bpmn-chor-app/src/ChorModelerApp.tsx';uls=(R/ui).read_text().splitlines();add('01_CIM_EXTENSION_MODEL.md',f'\n前端真实构造/迁移方法原始摘录：`{ui}:96`，commit `{sha}`\n\n```tsx\n'+'\n'.join(uls[95:208])+'\n```\n')
# Input/source verification against Git HEAD and copied original bytes.
checks=[]
for dest in (A/'source_references').rglob('*'):
 if not dest.is_file():continue
 rel=dest.relative_to(A/'source_references').as_posix();src=R/rel
 if not src.is_file():continue
 p=subprocess.run(['git','show','HEAD:'+rel],capture_output=True)
 checks.append({'path':rel,'copy_equal_worktree':dest.read_bytes()==src.read_bytes(),'worktree_equal_HEAD':p.returncode==0 and p.stdout==src.read_bytes()})
for sub in ['new/SupplyChainPaper.bpmn','new/supplyChainPaper.dmn','SupplyChainPaper.bpmn','supplyChainPaper.dmn']:
 rel='Experiment/BPMNwithDMNcase/'+sub;p=subprocess.run(['git','show','HEAD:'+rel],capture_output=True);checks.append({'path':rel,'copy_equal_worktree':(A/'source_models'/sub).read_bytes()==(R/rel).read_bytes(),'worktree_equal_HEAD':p.returncode==0 and p.stdout==(R/rel).read_bytes()})
write('logs/source_integrity.json',json.dumps(checks,indent=2));assert all(x['copy_equal_worktree'] and x['worktree_equal_HEAD'] for x in checks)
p=subprocess.run(['git','status','--short','--branch'],capture_output=True,text=True);write('logs/final_git_status.txt',p.stdout)
# Review bundle: substantive documents, real models/PIM/contexts, focused excerpts and source templates.
B=A/'review_bundle'
for src in [*A.glob('0*.md'),f,A/'source_models/new/SupplyChainPaper.bpmn',A/'source_models/new/supplyChainPaper.dmn',A/'generated_pim/SupplyChainPaper.b2c',A/'generation_contexts/fabric.diagnostic.json',A/'generation_contexts/geth.diagnostic.json',A/'logs/stage_status.json',A/'logs/cim_read_audit.json',A/'source_references'/GT,A/'source_references'/ST,A/'source_references/src/bpmn-chor-app/src/modeler/moddle/abc.json']:
 if src.name.endswith('.md') or src==f:dest=B/src.name
 else:dest=B/src.relative_to(A)
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
# Small standalone extract artifact mirrors reviewed mapping text (labelled excerpt).
for doc in ['06_BUSINESSRULE_WORKED_MAPPING.md','07_OTHER_PATTERN_EXAMPLES.md']:
 shutil.copy2(A/doc,A/'template_extracts'/doc)
write('review_bundle/README.md','阅读顺序：00→01→04→06→08；各 md 为主归档的原文副本。source_models 与 generated_pim 为本次真实原始文件；context 为非原生诊断；模板保留真实语法。完整生成代码及源码定位在主归档，不将 ZIP 当作编译通过证明。\n')
manifest=[]
for p in sorted(A.rglob('*')):
 if not p.is_file() or p.name in ['manifest.csv','review_bundle.zip']:continue
 rel=p.relative_to(A).as_posix();origin='diagnostic/report generated in this task'
 if rel.startswith('source_references/src/'):origin=rel[len('source_references/'):]
 elif rel.startswith('source_models/'):origin='Experiment/BPMNwithDMNcase/'+rel[len('source_models/'):]
 elif rel.startswith('source_references/historical_'):origin='f98238e8:docs/SupplyChainPaper/SupplyChainPaper_20260922_133943/'
 manifest.append([rel,origin,sha,hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_size])
with (A/'manifest.csv').open('w',newline='',encoding='utf-8-sig') as out:w=csv.writer(out);w.writerow(['artifact_path','source_path_or_kind','current_commit','sha256','bytes']);w.writerows(manifest)
shutil.copy2(A/'manifest.csv',B/'manifest.full_archive.csv')
with zipfile.ZipFile(A/'review_bundle.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(B.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(A))
with zipfile.ZipFile(A/'review_bundle.zip') as z:assert z.testzip() is None
print(json.dumps({'archive':str(A),'zip':str(A/'review_bundle.zip'),'manifest_files':len(manifest),'source_integrity_files':len(checks),'zero_locations':[{k:v for k,v in r.items() if 'line' in k and v==0} for r in rows],'zip_bytes':(A/'review_bundle.zip').stat().st_size},indent=2))