from pathlib import Path
import argparse, subprocess, sys, os, json, hashlib, shutil, importlib.metadata
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(); parser.add_argument('phase',choices=['baseline','baseline_repeat','after','after_layout']); args=parser.parse_args()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
paths=[ROOT/'src',ROOT/'src/newTranslator',ROOT/'src/newTranslator/DSL/B2CDSL',ROOT/'src/newTranslator/CodeGenerator/b2cdsl-go',ROOT/'src/newTranslator/CodeGenerator/b2cdsl-solidity']
env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join(map(str,paths));env['PYTHONDONTWRITEBYTECODE']='1'
if args.phase=='baseline':
 if (HERE/'baseline').exists(): raise RuntimeError('Baseline already exists; do not overwrite')
 cases=[]
 for group,folder in [('legacy',ROOT/'Experiment/BPMNwithDMNcase'),('structured',ROOT/'Experiment/BPMNwithDMNcase/new')]:
  dest=HERE/'inputs'/group;dest.mkdir(parents=True,exist_ok=True)
  for p in sorted(folder.iterdir()):
   if p.suffix in ['.bpmn','.dmn']:shutil.copy2(p,dest/p.name)
  for p in sorted(dest.glob('*.bpmn')): cases.append({'id':group+'/'+p.stem,'input':str(p.relative_to(HERE)),'kind':'bpmn'})
 for name in ['Exclusive','Parallel','Event-based']:
  p=ROOT/'Experiment/CaseTest'/(name+'.bpmn');dest=HERE/'inputs/control'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(p,dest)
  cases.append({'id':'control/'+name,'input':str(dest.relative_to(HERE)),'kind':'bpmn'})
 p=ROOT/'src/bpmn-chor-app/src/assets/bpmns/oracleDiagram.bpmn';dest=HERE/'inputs/control'/p.name;shutil.copy2(p,dest)
 cases.append({'id':'control/oracleDiagram','input':str(dest.relative_to(HERE)),'kind':'bpmn'})
 # Additional explicitly test-only DSL fixture, saved before refactoring.
 fixture=HERE/'inputs/fixture/flow_template_regression.b2c'
 if fixture.exists():cases.append({'id':'fixture/flow_template_regression','input':str(fixture.relative_to(HERE)),'kind':'b2c'})
 shutil.copy2(ROOT/'src/newTranslator/generator/bindings.json',HERE/'inputs/bindings.json')
 write(HERE/'cases.json',cases)
 write(HERE/'inputs.sha256.json',{str(p.relative_to(HERE)):sha(p) for p in sorted((HERE/'inputs').rglob('*')) if p.is_file()})
 src=ROOT/'src/newTranslator/CodeGenerator/b2cdsl-solidity'
 shutil.copytree(src/'templates',HERE/'baseline_source/templates',dirs_exist_ok=True)
 shutil.copy2(src/'b2cdsl_solidity/__init__.py',HERE/'baseline_source/__init__.py')
 write(HERE/'environment.json',{'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'python':sys.version,'executable':sys.executable,'packages':{n:importlib.metadata.version(n) for n in ['textX','Jinja2','networkx']},'PYTHONPATH':env['PYTHONPATH'],'bindings':'src/newTranslator/generator/bindings.json','bindings_cli_override':None,'platform_configuration':'Native textX b2c -> go / solidity defaults; no external PSM or deployment configuration','git_status_before':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)})
inputs=json.loads((HERE/'inputs.sha256.json').read_text())
for p,h in inputs.items(): assert sha(HERE/p)==h,p
assert sha(ROOT/'src/newTranslator/generator/bindings.json')==inputs['inputs/bindings.json']
cases=json.loads((HERE/'cases.json').read_text());run=HERE/args.phase
if run.exists():raise RuntimeError('Run directory already exists: '+str(run))
run.mkdir();commands=[];failures=[]
def command(argv,log):
 r=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True)
 log.write_text(r.stdout+r.stderr,encoding='utf-8');commands.append({'argv':argv,'cwd':str(ROOT),'PYTHONPATH':env['PYTHONPATH'],'returncode':r.returncode,'log':str(log.relative_to(HERE))})
 if r.returncode:failures.append(commands[-1])
 return r.returncode
for case in cases:
 dest=run/case['id'];dest.mkdir(parents=True);p=HERE/case['input'];dsl=dest/(p.stem+'.b2c')
 if case['kind']=='bpmn':
  if command([sys.executable,str(ROOT/'src/newTranslator/generator/bpmn_to_dsl.py'),str(p),'-o',str(dsl),'-n',p.stem.replace(' ','_').replace('-','_')],dest/'cim_pim.log'):continue
 else:shutil.copy2(p,dsl)
 for target in ['go','solidity']:
  output=dest/target;output.mkdir()
  command([str(Path(sys.executable).parent/'textx'),'generate',str(dsl),'--target',target,'--output-path',str(output),'--overwrite'],dest/(target+'.log'))
manifest={str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file() and p.suffix not in ['.log']}
write(HERE/(args.phase+'.sha256.json'),manifest);write(HERE/(args.phase+'.commands.json'),commands)
result={'phase':args.phase,'cases':len(cases),'commands':len(commands),'files':len(manifest),'failures':failures}
if args.phase!='baseline':
 old=json.loads((HERE/'baseline.sha256.json').read_text());result['differences']=[{'file':p,'before':old.get(p),'after':manifest.get(p)} for p in sorted(set(old)|set(manifest)) if old.get(p)!=manifest.get(p)]
write(HERE/(args.phase+'.result.json'),result)
print(json.dumps(result,ensure_ascii=False))
sys.exit(1 if failures or result.get('differences') else 0)
