from pathlib import Path
import subprocess,sys,json,shutil,hashlib,os,traceback,importlib.metadata
R=Path('/home/shenxz-lab/code/ChainCollab'); os.chdir(R)
sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
A=R/'artifacts'/('TSC_SecIV_DevFork_Evidence_'+sha[:8]); A.mkdir(parents=True,exist_ok=True)
for d in ['source_models','generated_pim','generation_contexts','generated_fabric','generated_geth','template_extracts','source_references','logs','review_bundle']: (A/d).mkdir(exist_ok=True)
def write(p,s):
 p=A/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def run(label,args):
 p=subprocess.run(args,capture_output=True,text=True);write('logs/'+label+'.stdout',p.stdout);write('logs/'+label+'.stderr',p.stderr);write('logs/'+label+'.command.json',json.dumps({'argv':args,'cwd':str(R),'exit_code':p.returncode},indent=2));return p
run('initial_status',['git','status','--short','--branch']);run('refs',['git','show-ref','--heads']);run('python_versions',[sys.executable,'-m','pip','list','--format=json'])
write('logs/runtime.json',json.dumps({'python':sys.version,'executable':sys.executable,'commit':sha},indent=2))
for ref in ['f98238e8','release-MultiBlockchain']:
 run('diff_'+ref,['git','diff',ref,'HEAD','--','src/newTranslator/generator','src/newTranslator/DSL','src/newTranslator/CodeGenerator','src/bpmn-chor-app/src/modeler','Experiment/BPMNwithDMNcase'])
for f in ['README.md','evidence/issues.md','evidence/status.json','evidence/worked_mapping_extracts.md','evidence/provenance.json','evidence/traceability.csv']:
 p=run('history_'+Path(f).name,['git','show','f98238e8:docs/SupplyChainPaper/SupplyChainPaper_20260922_133943/'+f]);
 if p.returncode==0:write('source_references/historical_f98238e8/'+f,p.stdout)
paths=[]
for base in ['src/newTranslator/generator','src/newTranslator/DSL/B2CDSL/b2cdsl','src/newTranslator/CodeGenerator/b2cdsl-go','src/newTranslator/CodeGenerator/b2cdsl-solidity','src/bpmn-chor-app/src/modeler']:
 for p in (R/base).rglob('*'):
  if p.is_file() and not any(x in p.parts for x in ['__pycache__','.venv','node_modules','.git']) and p.suffix in ['.py','.tx','.jinja','.json','.js','.ts'] and p.name!='bindings.json' and 'resource' not in p.parts:paths.append(p)
for p in paths:
 dest=A/'source_references'/p.relative_to(R);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
for sub in ['new/SupplyChainPaper.bpmn','new/supplyChainPaper.dmn','SupplyChainPaper.bpmn','supplyChainPaper.dmn']:
 p=R/'Experiment/BPMNwithDMNcase'/sub;dest=A/'source_models'/sub;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
# Native CLI: absolute source, isolated output only.
p=run('cim_to_pim',[sys.executable,'src/newTranslator/generator/bpmn_to_dsl.py',str(R/'Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn'),'-o',str(A/'generated_pim/SupplyChainPaper.b2c')])
results={'cim_to_pim':p.returncode}
if p.returncode==0:
 for platform,folder in [('go','generated_fabric'),('solidity','generated_geth')]:
  p=run('native_'+platform,[str(Path(sys.executable).parent/'textx'),'generate',str(A/'generated_pim/SupplyChainPaper.b2c'),'--target',platform,'--output-path',str(A/folder),'--overwrite']);results[platform]=p.returncode
# Diagnostic context: fresh original renderer, no patches. Compare direct template expansion against native CLI bytes.
try:
 sys.path.insert(0,str(R/'src/newTranslator'))
 for d in ['DSL/B2CDSL','CodeGenerator/b2cdsl-go','CodeGenerator/b2cdsl-solidity']:sys.path.insert(0,str(R/'src/newTranslator'/d))
 from b2cdsl import b2c_language
 import b2cdsl_go as go,b2cdsl_solidity as sol
 from textx import metamodel_from_file; mm=metamodel_from_file(str(R/'src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx'));model=mm.model_from_file(str(A/'generated_pim/SupplyChainPaper.b2c'));results['grammar']='PASS'
 write('generation_contexts/pim_sections.json',json.dumps([{'section_type':type(s).__name__,'count':len(getattr(s,'items',[]))} for s in model.contracts[0].sections],indent=2))
 for platform,mod,folder,suffix in [('fabric',go,'generated_fabric','go'),('geth',sol,'generated_geth','sol')]:
  adapter=mod.DSLContractAdapter(model.contracts[0]);renderer=mod.GoChaincodeRenderer(adapter,mod.TEMPLATE_ENV) if platform=='fabric' else mod.SolidityRenderer(adapter)
  ctx=renderer.build_context();write('generation_contexts/'+platform+'.diagnostic.json',json.dumps(ctx,ensure_ascii=False,indent=2))
  rendered=mod.TEMPLATE_ENV.get_template(mod.CONTRACT_TEMPLATE).render(**ctx).strip()+'\n'
  native=A/folder/('SupplyChainPaper.'+suffix)
  results[platform+'_context_native_equal']=native.exists() and native.read_bytes()==rendered.encode()
except Exception:
 write('logs/diagnostic_error.txt',traceback.format_exc());results['diagnostic']='FAIL'
write('logs/stage_status.json',json.dumps(results,indent=2));print(str(A));print(json.dumps(results))