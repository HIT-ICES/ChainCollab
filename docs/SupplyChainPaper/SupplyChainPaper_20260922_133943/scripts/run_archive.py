import os, sys, json, hashlib, shutil, subprocess, datetime, csv
from pathlib import Path
R=Path('/home/shenxz-lab/code/ChainCollab'); T=R/'src/newTranslator'
O=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
O.mkdir(parents=True,exist_ok=True)
for d in ['logs','source_models','pim','fabric/raw','geth/raw','generation_contexts','evidence','existing_artifacts','generator_snapshot','scripts']:(O/d).mkdir(parents=True,exist_ok=True)
P=T/'.venv/bin/python'; env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(T),PATH=str(T/'.venv/bin')+':/usr/local/go/bin:'+env['PATH'])
provenance={}; status={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def cp(p,d,kind,stage):
 d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d);provenance[str(d.relative_to(O))]=[str(p),stage,kind]
def run(name,args,cwd=None,extra=None,timeout=180):
 e=env.copy();e.update(extra or {});cwd=cwd or O
 meta={'cwd':str(cwd),'argv':list(map(str,args)),'environment':{k:e[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','PATH']},'extra_environment':extra or {},'start':datetime.datetime.now().isoformat()}
 try:
  q=subprocess.run(list(map(str,args)),cwd=cwd,env=e,capture_output=True,timeout=timeout); code=q.returncode;so=q.stdout;se=q.stderr
 except subprocess.TimeoutExpired as x:code=124;so=x.stdout or b'';se=(x.stderr or b'')+b'\nTIMEOUT\n'
 except Exception as x:code=127;so=b'';se=str(x).encode()
 (O/f'logs/{name}.stdout').write_bytes(so);(O/f'logs/{name}.stderr').write_bytes(se);meta['exit_code']=code;meta['end']=datetime.datetime.now().isoformat();dump(O/f'logs/{name}.json',meta)
 print(name,code,flush=True);return code
run('git_before',['git','status','--porcelain=v1','--untracked-files=all'],R)
run('git_branch',['git','branch','--show-current'],R);run('git_commit',['git','rev-parse','HEAD'],R)
run('git_diff_stat',['git','diff','--stat'],R);run('git_cached_diff_stat',['git','diff','--cached','--stat'],R)
run('python_version',[P,'--version']);run('pip_freeze',[P,'-m','pip','freeze']);run('go_version',['/usr/local/go/bin/go','version']);run('tool_discovery',['bash','-c','command -v go solc solcjs node npm; find /home/shenxz-lab/.solcx /home/shenxz-lab/.nvm -name solcjs -o -name soljson.js 2>/dev/null'],timeout=30)
inputs=[R/'Experiment/BPMNwithDMNcase/SupplyChainPaper.bpmn',R/'Experiment/BPMNwithDMNcase/supplyChainPaper.dmn']
for p in inputs:cp(p,O/'source_models'/p.name,'source','inputs')
status['input_check']='PASS'
# Restrict snapshot to converter, grammar, renderers, templates, declared dependencies and helper entrypoints.
selected=[]
for base in [T/'generator',T/'DSL/B2CDSL',T/'CodeGenerator/b2cdsl-go',T/'CodeGenerator/b2cdsl-solidity']:
 for p in base.rglob('*'):
  if not p.is_file() or any(x in p.parts for x in ['__pycache__','.git','.venv','node_modules']):continue
  rel=p.relative_to(T)
  if 'resource' in rel.parts and not ('contracts' in rel.parts or p.name in ['go.mod','go.sum']):continue
  if p.suffix not in ['.py','.tx','.jinja','.json','.toml','.md','.sh','.go'] and p.name not in ['go.mod','go.sum']:continue
  selected.append(p)
selected += [T/'README.md',T/'nt.sh',T/'newTranslator_devtools.sh',T/'requirements.txt']
for p in selected:
 if p.exists():cp(p,O/'generator_snapshot'/p.relative_to(R),'source','snapshot')
dump(O/'evidence/protected_hashes_before.json',{str(p):sha(p) for p in inputs+selected if p.exists()})
# Read-only historical search: filename AND model IDs. Exclude dependency stores and this archive.
needles=[b'Activity_0rm8bkp',b'Gateway_0ep8cuh',b'decision_0tybghz',b'Decision_0zwjfyy']
search=[]
for base,dirs,files in os.walk(R):
 dirs[:]=[d for d in dirs if d not in ['.git','.venv','node_modules','pgdata','artifacts','__pycache__','venv','.next']]
 for fn in files:
  p=Path(base)/fn
  if p.suffix.lower() not in ['.b2c','.bpmn','.dmn','.go','.sol','.json','.py','.sh','.md','.csv','.txt','.xmi','.yaml','.yml']:continue
  try:
   if p.stat().st_size>4_000_000:continue
   b=p.read_bytes(); hits=[n.decode() for n in needles if n in b]
  except (OSError,PermissionError):continue
  if hits or 'supplychainpaper' in fn.lower():search.append({'path':str(p.relative_to(R)),'hits':hits,'filename_match':'supplychainpaper' in fn.lower(),'sha256':hashlib.sha256(b).hexdigest()})
dump(O/'evidence/historical_candidates.json',search)
# Copy only candidates with both distinctive BPMN IDs; DMN requires both decision IDs. Other candidates remain indexed, not asserted as matching.
for row in search:
 p=R/row['path'];h=row['hits']
 confirmed=('Activity_0rm8bkp' in h and 'Gateway_0ep8cuh' in h) or ('decision_0tybghz' in h and 'Decision_0zwjfyy' in h)
 if confirmed and p not in inputs and p.suffix.lower() in ['.b2c','.go','.sol','.json','.dmn','.py','.sh','.md','.csv','.txt']:
  cp(p,O/'existing_artifacts'/row['path'],'historical','historical');row['archived']=True;row['correspondence']='Both distinctive IDs match; historical variant, not byte-equivalent model certification.'
dump(O/'evidence/historical_candidates.json',search)
b2c=O/'pim/SupplyChainPaper.b2c'
a=run('A_bpmn_to_dsl',[P,T/'generator/bpmn_to_dsl.py',inputs[0],'-o',b2c]);status['bpmn_to_dsl']='PASS' if a==0 and b2c.exists() else 'FAIL'
if b2c.exists():
 status['dsl_parse']='PASS' if run('A_parse',[T/'.venv/bin/textx','check',b2c])==0 else 'FAIL'
 dump(O/'evidence/platform_pim_hashes.json',{k:{'input':str(b2c),'sha256':sha(b2c)} for k in ['fabric','geth']})
 status['go_generation']='PASS' if run('B_go_generate',[T/'.venv/bin/textx','generate',b2c,'--target','go','--overwrite','-o',O/'fabric/raw'])==0 else 'FAIL'
 status['solidity_generation']='PASS' if run('C_solidity_generate',[P,T/'generator/b2c_to_solidity.py',b2c,'-o',O/'geth/raw/SupplyChainPaper.sol'])==0 else 'FAIL'
 status['context_export']='PASS' if run('D_diagnostic',[P,O/'scripts/diagnostic.py',O])==0 else 'FAIL'
 if (O/'fabric/raw/SupplyChainPaper.go').exists():
  shutil.copytree(O/'fabric/raw',O/'fabric/compile_copy',dirs_exist_ok=True)
  status['go_compile']='PASS' if run('B_go_compile',['/usr/local/go/bin/go','build','-mod=readonly','./...'],O/'fabric/compile_copy',{'GOTOOLCHAIN':'local','GOCACHE':str(O/'fabric/build_cache')},240)==0 else 'FAIL'
 else:status['go_compile']='BLOCKED'
 solc=shutil.which('solc',path=env['PATH'])
 if solc:
  run('solc_version',[solc,'--version'])
  status['solidity_compile']='PASS' if run('C_solidity_compile',[solc,'--bin','--abi','--metadata','--optimize','-o',O/'geth/compiled',O/'geth/raw/SupplyChainPaper.sol'])==0 else 'FAIL'
 else:status['solidity_compile']='BLOCKED'
else:
 for k in ['dsl_parse','go_generation','solidity_generation','context_export','go_compile','solidity_compile']:status[k]='BLOCKED'
status['onchain_execution']='NOT_RUN'
dump(O/'evidence/status.json',status);dump(O/'evidence/provenance.json',provenance)
dump(O/'evidence/protected_hashes_after.json',{str(p):sha(p) for p in inputs+selected if p.exists()})
run('git_after',['git','status','--porcelain=v1','--untracked-files=all'],R)
print(json.dumps(status),flush=True)
