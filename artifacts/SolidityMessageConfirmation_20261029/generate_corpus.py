from pathlib import Path
import sys,subprocess,os,json,hashlib
r=Path('/home/shenxz-lab/code/ChainCollab');e=r/'artifacts/SolidityMessageConfirmation_20261029';old=r/'artifacts/SolidityJinjaRefactor_20261029';py=r/'src/newTranslator/.venv/bin/python';env=os.environ.copy()
env['PYTHONPATH']=':'.join(str(r/p) for p in ['src','src/newTranslator','src/newTranslator/DSL/B2CDSL','src/newTranslator/CodeGenerator/b2cdsl-solidity','src/newTranslator/CodeGenerator/b2cdsl-go']);env['PYTHONDONTWRITEBYTECODE']='1'
cases=json.loads((old/'cases.json').read_text());cases.append({'id':'fixture/message_confirmation','input':str(r/'src/newTranslator/CodeGenerator/b2cdsl-solidity/tests/fixtures/message_confirmation.b2c'),'kind':'b2c'})
results=[]
for case in cases:
 dest=e/'generated'/case['id'];dest.mkdir(parents=True,exist_ok=True);src=Path(case['input']);src=src if src.is_absolute() else old/src
 dsl=dest/(src.stem+'.b2c');commands=[]
 if case['kind']=='bpmn':commands.append([str(py),str(r/'src/newTranslator/generator/bpmn_to_dsl.py'),str(src),'-o',str(dsl),'-n',src.stem.replace(' ','_').replace('-','_')])
 else:dsl.write_bytes(src.read_bytes())
 commands.append([str(py.parent/'textx'),'generate',str(dsl),'--target','solidity','--output-path',str(dest),'--overwrite'])
 for idx,cmd in enumerate(commands):
  result=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True);(dest/f'command_{idx}.log').write_text(result.stdout+result.stderr);results.append({'case':case['id'],'argv':cmd,'returncode':result.returncode});assert result.returncode==0,results[-1]
 if case['id']!='fixture/message_confirmation':
  original=old/'baseline'/case['id']/dsl.name;assert dsl.read_bytes()==original.read_bytes(),str(dsl)
manifest={str(p.relative_to(e)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (e/'generated').rglob('*') if p.suffix in ['.sol','.b2c']}
(e/'generation_commands.json').write_text(json.dumps(results,indent=2)+'\n');(e/'generated.sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Generated',len(cases),'Solidity cases; all existing PIM outputs unchanged.')
